<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { loadKatex, getKatexCssUrl } from '$lib/utils/katexLoader';
	import { loadCodeMirrorModules, createEditorExtensions, type CodeMirrorModules } from '$lib/utils/codemirror';
	import { theme } from '$lib/stores/themeStore';
	import { processCrossRefs, lookupRef, crossrefIndexStore } from '$lib/utils/crossref';
	import { searchTarget } from '$lib/stores/searchNavigation';
	import { createCopyButton } from '$lib/utils/copyButton';

	interface Props {
		html: string;
	}

	let { html }: Props = $props();

	// Process HTML for cross-references (reactive to store changes)
	let processedHtml = $derived.by(() => {
		// Subscribe to crossref store to trigger re-processing when index loads
		$crossrefIndexStore;
		return rewriteFigures(processCrossRefs(html, base), base);
	});

	// Docstring figures are emitted by the build as root-relative paths
	// ("{package}/{tag}/figures/..."). Prefix the deployment base so they resolve
	// from the site root (not the current route), and lazy-load them.
	function rewriteFigures(rawHtml: string, basePath: string): string {
		return rawHtml.replace(/<img\b[^>]*>/gi, (tag) => {
			let t = tag.replace(
				/(\ssrc=["'])([^"']+)(["'])/i,
				(m, pre, src, post) => {
					if (
						/^(https?:)?\/\//i.test(src) ||
						src.startsWith('data:') ||
						src.startsWith('/') ||
						(basePath && src.startsWith(basePath + '/'))
					) {
						return m;
					}
					return `${pre}${basePath}/${src}${post}`;
				}
			);
			if (!/\bloading=/i.test(t)) {
				t = t.replace(/^<img\b/i, '<img loading="lazy"');
			}
			return t;
		});
	}

	let container: HTMLDivElement | undefined = $state();
	let katexLoaded = $state(false);
	let cmModules: CodeMirrorModules | null = null;
	let editorViews: import('@codemirror/view').EditorView[] = [];

	// Store code content and container refs for theme switching
	let codeBlocks: { wrapper: HTMLElement; code: string }[] = [];

	// Render math with KaTeX (same approach as PathView)
	async function renderMath() {
		if (!container) return;

		const k = await loadKatex();
		katexLoaded = true;

		// Find all math elements - docutils MathJax output uses <div class="math"> with LaTeX content
		const mathElements = container.querySelectorAll('.math');

		for (const el of mathElements) {
			// Skip if already rendered
			if (el.classList.contains('katex-rendered')) continue;

			const latex = el.textContent || '';
			if (!latex.trim()) continue;

			try {
				// Clean up the LaTeX
				let cleaned = latex
					.replace(/^\\\(|\\\)$/g, '')  // Remove \( \) delimiters
					.replace(/^\\\[|\\\]$/g, '')  // Remove \[ \] delimiters
					.trim();

				// Convert unsupported environments
				cleaned = cleaned
					.replace(/\\begin\{eqnarray\*?\}/g, '\\begin{aligned}')
					.replace(/\\end\{eqnarray\*?\}/g, '\\end{aligned}');

				// Wrap multi-line equations in aligned environment if not already wrapped
				if (cleaned.includes('\\\\') && !cleaned.includes('\\begin{')) {
					cleaned = `\\begin{aligned}${cleaned}\\end{aligned}`;
				}

				const isDisplay = el.tagName === 'DIV' || el.tagName === 'PRE' || latex.includes('\\[');

				const rendered = k.default.renderToString(cleaned, {
					displayMode: isDisplay,
					throwOnError: false,
					strict: false
				});

				el.innerHTML = rendered;
				el.classList.add('katex-rendered');
			} catch (e) {
				console.warn('KaTeX error for:', latex, e);
				// Leave original content
			}
		}
	}

	// Create a type span with cross-reference links for class names
	function createTypeWithRefs(typeText: string): HTMLElement {
		const span = document.createElement('span');
		span.className = 'type-ref';

		// Split by type syntax characters while preserving them
		const tokens = typeText.split(/(\[|\]|,\s*|\s*\|\s*)/);

		for (const token of tokens) {
			if (!token) continue;

			// Check if this token looks like a class name (PascalCase)
			if (/^[A-Z][a-zA-Z0-9_]*$/.test(token)) {
				const target = lookupRef(token);
				if (target) {
					const link = document.createElement('a');
					const fullPath = `${base}/${target.path}`;
					link.href = fullPath;
					link.className = 'type-link';
					link.textContent = token;
					link.addEventListener('click', (e) => {
						e.preventDefault();
						searchTarget.set({
							name: target.name,
							type: target.type as 'class' | 'function' | 'method' | 'module',
							source: 'crossref'
						});
						goto(fullPath);
					});
					span.appendChild(link);
				} else {
					span.appendChild(document.createTextNode(token));
				}
			} else {
				span.appendChild(document.createTextNode(token));
			}
		}

		return span;
	}

	// Transform definition lists to tables
	function transformDefinitionListsToTables() {
		if (!container) return;

		const dlElements = container.querySelectorAll('dl.docutils');

		for (const dl of dlElements) {
			// Skip if already transformed
			if (dl.classList.contains('table-transformed')) continue;

			// Create wrapper for panel styling
			const wrapper = document.createElement('div');
			wrapper.className = 'param-table-wrapper';

			const table = document.createElement('table');
			table.className = 'param-table';

			// Add header row
			const thead = document.createElement('thead');
			const headerRow = document.createElement('tr');
			['Name', 'Type', 'Description'].forEach(text => {
				const th = document.createElement('th');
				th.textContent = text;
				headerRow.appendChild(th);
			});
			thead.appendChild(headerRow);
			table.appendChild(thead);

			const tbody = document.createElement('tbody');

			// Get all dt/dd pairs
			const dts = dl.querySelectorAll(':scope > dt');

			for (const dt of dts) {
				const row = document.createElement('tr');

				// Extract name (text before classifier-delimiter)
				const nameCell = document.createElement('td');
				nameCell.className = 'param-name';
				const nameCode = document.createElement('code');

				// Get the name - it's the first text node or text before classifier-delimiter
				let name = '';
				for (const node of dt.childNodes) {
					if (node.nodeType === Node.TEXT_NODE) {
						name = node.textContent?.trim() || '';
						if (name) break;
					} else if (node.nodeType === Node.ELEMENT_NODE) {
						const el = node as Element;
						if (el.classList.contains('classifier-delimiter')) break;
						name = el.textContent?.trim() || '';
						if (name) break;
					}
				}
				nameCode.textContent = name;
				nameCell.appendChild(nameCode);
				row.appendChild(nameCell);

				// Extract type from classifier span and add cross-references
				const typeCell = document.createElement('td');
				typeCell.className = 'param-type';
				const classifier = dt.querySelector('.classifier');
				if (classifier) {
					const typeText = classifier.textContent || '';
					typeCell.appendChild(createTypeWithRefs(typeText));
				}
				row.appendChild(typeCell);

				// Get description from following dd
				const descCell = document.createElement('td');
				descCell.className = 'param-desc';
				const dd = dt.nextElementSibling;
				if (dd && dd.tagName === 'DD') {
					descCell.innerHTML = dd.innerHTML;
				}
				row.appendChild(descCell);

				tbody.appendChild(row);
			}

			table.appendChild(tbody);
			wrapper.appendChild(table);

			// Replace dl with wrapped table
			dl.parentNode?.replaceChild(wrapper, dl);
		}
	}

	// Detect language from code content
	function detectLanguage(code: string): 'python' | 'console' {
		// Check for Python REPL prompts
		if (code.includes('>>>') || code.includes('...')) {
			return 'console';
		}
		return 'python';
	}

	// Render code blocks with CodeMirror
	async function renderCodeBlocks() {
		if (!container) return;

		// Clean up existing editors
		for (const view of editorViews) {
			view.destroy();
		}
		editorViews = [];
		codeBlocks = [];

		cmModules = await loadCodeMirrorModules();
		const isDark = document.documentElement.getAttribute('data-theme') !== 'light';

		// Find all pre elements that contain code
		// Handles: <pre><code>...</code></pre> and <pre class="code">...</pre>
		const preElements = container.querySelectorAll('pre');

		for (const preEl of preElements) {
			// Skip if already processed or is math content
			if (preEl.classList.contains('cm-processed')) continue;
			if (preEl.classList.contains('math')) continue;

			// Get code content - either from nested code element or directly from pre
			const codeEl = preEl.querySelector('code');
			const code = codeEl ? codeEl.textContent : preEl.textContent;
			if (!code?.trim()) continue;

			// Mark as processed
			preEl.classList.add('cm-processed');

			const trimmedCode = code.trim();
			const language = detectLanguage(trimmedCode);

			// Create wrapper div
			const wrapper = document.createElement('div');
			wrapper.className = 'code-block-wrapper';

			// Create header
			const header = document.createElement('div');
			header.className = 'code-block-header';

			const label = document.createElement('span');
			label.className = 'label-uppercase';
			label.textContent = language === 'console' ? 'CONSOLE' : 'PYTHON';
			header.appendChild(label);

			header.appendChild(createCopyButton(trimmedCode));
			wrapper.appendChild(header);

			// Create editor container
			const editorDiv = document.createElement('div');
			editorDiv.className = 'cm-container';
			wrapper.appendChild(editorDiv);

			// Replace pre with wrapper
			preEl.parentNode?.replaceChild(wrapper, preEl);

			// Store code and wrapper for theme switching
			codeBlocks.push({ wrapper, code: trimmedCode });

			// Create CodeMirror editor
			const view = new cmModules.EditorView({
				doc: trimmedCode,
				extensions: createEditorExtensions(cmModules, isDark, { readOnly: true }),
				parent: editorDiv
			});

			editorViews.push(view);
		}
	}

	// Update existing code blocks with new theme
	async function updateCodeBlockTheme() {
		if (!cmModules || codeBlocks.length === 0) return;

		const isDark = document.documentElement.getAttribute('data-theme') !== 'light';

		// Destroy old editors
		for (const view of editorViews) {
			view.destroy();
		}
		editorViews = [];

		// Recreate editors with new theme
		for (const { wrapper, code } of codeBlocks) {
			const editorDiv = wrapper.querySelector('.cm-container');
			if (!editorDiv) continue;

			// Clear old editor content
			editorDiv.innerHTML = '';

			// Create new editor with updated theme
			const view = new cmModules.EditorView({
				doc: code,
				extensions: createEditorExtensions(cmModules, isDark, { readOnly: true }),
				parent: editorDiv as HTMLElement
			});

			editorViews.push(view);
		}
	}

	// Track if we've done initial render
	let hasRendered = false;

	onMount(() => {
		// Add KaTeX CSS
		if (!document.querySelector('link[href*="katex"]')) {
			const link = document.createElement('link');
			link.rel = 'stylesheet';
			link.href = getKatexCssUrl();
			document.head.appendChild(link);
		}

		return () => {
			for (const view of editorViews) {
				view.destroy();
			}
			editorViews = [];
			codeBlocks = [];
		};
	});

	// Watch for theme changes to update code block themes
	$effect(() => {
		const currentTheme = $theme;
		// Only update if we have existing editors
		if (codeBlocks.length > 0) {
			updateCodeBlockTheme();
		}
	});

	// Render when container is ready and html is set
	$effect(() => {
		// Access html to create dependency
		const currentHtml = html;

		if (currentHtml && container && !hasRendered) {
			hasRendered = true;
			tick().then(() => {
				transformDefinitionListsToTables();
				renderMath();
				renderCodeBlocks();
			});
		}
	});

	// Handle clicks on cross-reference links
	function handleCrossRefClick(event: MouseEvent) {
		const target = event.target as HTMLElement;
		const link = target.closest('a.crossref') as HTMLAnchorElement;

		if (link) {
			event.preventDefault();
			const href = link.getAttribute('href');
			if (!href) return;

			// Extract the target name from the hash
			const hashIndex = href.indexOf('#');
			if (hashIndex >= 0) {
				const targetName = href.slice(hashIndex + 1);
				const linkType = link.classList.contains('crossref-class') ? 'class'
					: link.classList.contains('crossref-function') ? 'function'
					: link.classList.contains('crossref-method') ? 'method'
					: 'module';

				// Set search target to trigger expansion/scroll
				searchTarget.set({
					name: targetName,
					type: linkType as 'class' | 'function' | 'method' | 'module',
					source: 'crossref'
				});
			}

			// Navigate to the path
			goto(href);
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
<div class="docstring-content" bind:this={container} onclick={handleCrossRefClick}>
	{@html processedHtml}
</div>

<style>
	.docstring-content {
		font-size: var(--font-base);
		line-height: 1.7;
		color: var(--text-muted);
	}

	.docstring-content :global(p) {
		margin-bottom: 0.75em;
	}

	.docstring-content :global(p:last-child) {
		margin-bottom: 0;
	}

	/* Docstring figures */
	.docstring-content :global(img) {
		max-width: 100%;
		height: auto;
		display: block;
		margin: var(--space-md, 1rem) auto;
	}

	/* TikZ diagrams are SVG files (referenced by <img>) recolored at build time to
	   the muted text color on a transparent background, so they blend into the
	   prose with no container needed. */
	/* Width is set per-diagram in em (font-relative) on the element itself; we
	   only center it and cap it so it never overflows the column. */
	.docstring-content :global(img.tikz-figure) {
		display: block;
		max-width: 100%;
		height: auto;
		margin: var(--space-md, 1rem) auto;
	}

	/* Code block styles are in app.css */

	/* Parameter/Attribute tables - panel style */
	.docstring-content :global(.param-table-wrapper) {
		margin: var(--space-md) 0;
		overflow-x: auto;
	}

	.docstring-content :global(.param-table) {
		width: 100%;
		border-collapse: separate;
		border-spacing: 0;
		font-size: var(--font-base);
		table-layout: auto;
	}

	/* Header styled like panel-header */
	.docstring-content :global(.param-table thead th) {
		padding: var(--space-xs) var(--space-md);
		background: var(--surface-raised);
		font-size: var(--font-base);
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		text-align: left;
		border: 1px solid var(--border);
		border-right: none;
	}

	.docstring-content :global(.param-table thead th:last-child) {
		border-right: 1px solid var(--border);
		border-top-right-radius: var(--radius-lg);
	}

	.docstring-content :global(.param-table thead th:first-child) {
		border-top-left-radius: var(--radius-lg);
	}

	.docstring-content :global(.param-table td) {
		padding: var(--space-xs) var(--space-md);
		background: var(--surface);
		vertical-align: top;
		border-left: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
	}

	.docstring-content :global(.param-table td:last-child) {
		border-right: 1px solid var(--border);
	}

	/* Rounded corners on last row */
	.docstring-content :global(.param-table tbody tr:last-child td:first-child) {
		border-bottom-left-radius: var(--radius-lg);
	}

	.docstring-content :global(.param-table tbody tr:last-child td:last-child) {
		border-bottom-right-radius: var(--radius-lg);
	}

	.docstring-content :global(.param-table .param-name) {
		white-space: nowrap;
	}

	.docstring-content :global(.param-table .param-name code) {
		font-family: var(--font-mono);
		font-size: var(--font-base);
		font-weight: 500;
		color: var(--accent);
		background: none;
		border: none;
		padding: 0;
	}

	.docstring-content :global(.param-table .param-type) {
		word-break: break-word;
	}

	.docstring-content :global(.param-table .param-type code) {
		font-family: var(--font-mono);
		font-size: var(--font-base);
		color: var(--text-muted);
		background: none;
		border: none;
		padding: 0;
		word-break: break-word;
	}

	/* Type references in parameter tables */
	.docstring-content :global(.param-table .type-ref) {
		font-family: var(--font-mono);
		font-size: var(--font-base);
		color: var(--text-muted);
		word-break: break-word;
	}

	.docstring-content :global(.param-table .type-link) {
		color: var(--accent);
		font-weight: 500;
		text-decoration: none;
	}

	.docstring-content :global(.param-table .type-link:hover) {
		text-decoration: underline;
	}

	.docstring-content :global(.param-table .param-desc) {
		color: var(--text-muted);
		line-height: 1.5;
	}

	/* Generic dl fallback */
	.docstring-content :global(dl:not(.docutils)) {
		margin: var(--space-md) 0;
	}

	.docstring-content :global(dl:not(.docutils) dt) {
		font-family: var(--font-mono);
		font-size: var(--font-base);
		color: var(--accent);
		margin-top: var(--space-sm);
		font-weight: 500;
	}

	.docstring-content :global(dl:not(.docutils) dd) {
		margin-left: var(--space-lg);
		color: var(--text-muted);
		margin-top: var(--space-xs);
	}

	/* Lists */
	.docstring-content :global(ul),
	.docstring-content :global(ol) {
		margin: var(--space-sm) 0;
		padding-left: var(--space-xl);
	}

	.docstring-content :global(li) {
		margin-bottom: var(--space-xs);
	}

	/* RST section containers - separator ABOVE, extends to panel edges */
	.docstring-content :global(.section) {
		position: relative;
		margin-top: var(--space-lg);
		padding-top: var(--space-lg);
	}

	.docstring-content :global(.section::before) {
		content: '';
		position: absolute;
		top: 0;
		left: calc(-1 * var(--space-lg));
		width: calc(100% + 2 * var(--space-lg));
		height: 1px;
		background: var(--border);
	}

	.docstring-content :global(.section:first-child) {
		margin-top: var(--space-md);
		padding-top: 0;
	}

	.docstring-content :global(.section:first-child::before) {
		display: none;
	}

	/* Section headers - consistent style for h3, h4 */
	.docstring-content :global(h3),
	.docstring-content :global(h4) {
		font-family: var(--font-ui);
		font-size: var(--font-base);
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin: 0 0 var(--space-sm) 0;
		padding: 0;
		border: none;
	}

	/* NumPy-style section headers converted to <p><strong> - separator ABOVE, extends to panel edges */
	.docstring-content :global(p:has(> strong:only-child)) {
		position: relative;
		font-family: var(--font-ui);
		font-size: var(--font-base);
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-top: var(--space-lg);
		margin-bottom: var(--space-sm);
		padding-top: var(--space-lg);
	}

	.docstring-content :global(p:has(> strong:only-child)::before) {
		content: '';
		position: absolute;
		top: 0;
		left: calc(-1 * var(--space-lg));
		width: calc(100% + 2 * var(--space-lg));
		height: 1px;
		background: var(--border);
	}

	.docstring-content :global(p:first-child:has(> strong:only-child)) {
		margin-top: 0;
		padding-top: 0;
	}

	.docstring-content :global(p:first-child:has(> strong:only-child)::before) {
		display: none;
	}

	/* Ensure strong inside header paragraphs inherits style */
	.docstring-content :global(p:has(> strong:only-child) > strong) {
		font-weight: inherit;
		color: inherit;
	}

	.docstring-content :global(strong) {
		font-weight: 600;
	}

	/* KaTeX styling - use default sizing (~1.21em for better math readability) */
	.docstring-content :global(.katex) {
		/* Let KaTeX use its default font-size */
	}

	.docstring-content :global(.katex-display) {
		margin: var(--space-md) 0;
		overflow-x: auto;
	}

	/* Math fallback (before KaTeX renders) */
	.docstring-content :global(.katex-error),
	.docstring-content :global(.math:not(.katex-rendered)) {
		font-family: var(--font-mono);
		font-size: var(--font-base);
		color: var(--text-muted);
	}

	/* Math container styling */
	.docstring-content :global(div.math) {
		margin: var(--space-md) 0;
		text-align: center;
	}

	/* Tables */
	.docstring-content :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin: var(--space-md) 0;
		font-size: var(--font-base);
	}

	.docstring-content :global(th),
	.docstring-content :global(td) {
		padding: var(--space-xs) var(--space-sm);
		border: 1px solid var(--border);
		text-align: left;
	}

	.docstring-content :global(th) {
		background: var(--surface-raised);
		font-weight: 600;
		color: var(--text-muted);
	}

	/* Inline code */
	.docstring-content :global(code) {
		font-family: var(--font-mono);
		font-size: var(--font-base);
		background: var(--surface-raised);
		padding: 1px 4px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
	}

	/* Don't style code inside pre/codemirror */
	.docstring-content :global(pre code),
	.docstring-content :global(.cm-content code) {
		background: none;
		padding: 0;
		border: none;
		border-radius: 0;
	}

	/* Blockquote */
	.docstring-content :global(blockquote) {
		margin: var(--space-md) 0;
		padding-left: var(--space-md);
		border-left: 3px solid var(--accent);
		color: var(--text-muted);
	}

	/* Cross-reference links - base styles in app.css, only add hover effects for code */
	.docstring-content :global(a.crossref code) {
		background: var(--accent-bg);
		border-color: var(--accent);
	}

	.docstring-content :global(a.crossref:hover code) {
		background: var(--accent);
		color: white;
	}
</style>
