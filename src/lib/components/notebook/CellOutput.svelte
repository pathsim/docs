<script lang="ts">
	/**
	 * CellOutput - Renders static output from notebook cells
	 * Handles stream, execute_result, display_data, and error outputs
	 * Supports both inline base64 images and external figure URLs
	 */
	import type { CellOutput } from '$lib/notebook/types';
	import { getOutputText } from '$lib/notebook/parser';

	interface Props {
		outputs: CellOutput[];
		/** URLs of figures from pre-computed outputs */
		figureUrls?: string[];
		/** Text output from pre-computed outputs */
		precomputedStdout?: string | null;
		/** Stderr from pre-computed outputs */
		precomputedStderr?: string | null;
	}

	let { outputs, figureUrls = [], precomputedStdout, precomputedStderr }: Props = $props();

	// Show pre-computed text outputs
	let hasPrecomputedOutput = $derived(
		precomputedStdout || precomputedStderr || figureUrls.length > 0
	);

	/**
	 * Convert ANSI escape codes to HTML spans
	 * Handles basic colors used in Python tracebacks
	 */
	function ansiToHtml(text: string): string {
		// ANSI color codes mapping
		const colors: Record<string, string> = {
			'30': 'color: #4e4e4e', // black
			'31': 'color: var(--error)', // red
			'32': 'color: var(--success)', // green
			'33': 'color: var(--warning)', // yellow
			'34': 'color: var(--accent)', // blue
			'35': 'color: #a855f7', // magenta
			'36': 'color: #06b6d4', // cyan
			'37': 'color: var(--text)', // white
			'1': 'font-weight: bold',
			'0': '' // reset
		};

		// Replace ANSI codes with spans
		let result = text;

		// Match \x1b[...m patterns (ANSI escape sequences)
		result = result.replace(/\x1b\[([0-9;]+)m/g, (_, codesStr) => {
			const codes = codesStr.split(';');
			const styles = codes.map((c: string) => colors[c] || '').filter(Boolean);

			if (styles.length === 0 || codes.includes('0')) {
				return '</span>';
			}
			return `<span style="${styles.join('; ')}">`;
		});

		// Clean up any unclosed spans
		const openCount = (result.match(/<span/g) || []).length;
		const closeCount = (result.match(/<\/span>/g) || []).length;
		result += '</span>'.repeat(Math.max(0, openCount - closeCount));

		return result;
	}

	/**
	 * Escape HTML entities
	 */
	function escapeHtml(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#039;');
	}
</script>

{#if hasPrecomputedOutput || outputs.length > 0}
	<div class="cell-outputs">
		<!-- Pre-computed outputs (from separate outputs JSON) -->
		{#if precomputedStdout}
			<div class="output-stream">
				<pre>{precomputedStdout}</pre>
			</div>
		{/if}

		{#if precomputedStderr}
			<div class="output-stream stderr">
				<pre>{precomputedStderr}</pre>
			</div>
		{/if}

		{#each figureUrls as figureUrl}
			<div class="output-image">
				<img src={figureUrl} alt="Output" />
			</div>
		{/each}

		<!-- Inline notebook outputs (from notebook file) -->
		{#each outputs as output}
			{#if output.output_type === 'stream'}
				<div class="output-stream" class:stderr={output.name === 'stderr'}>
					<pre>{getOutputText(output.text)}</pre>
				</div>
			{:else if output.output_type === 'execute_result' || output.output_type === 'display_data'}
				{#if output.data['image/png']}
					<div class="output-image">
						<img src="data:image/png;base64,{output.data['image/png']}" alt="Output" />
					</div>
				{:else if output.data['image/svg+xml']}
					<div class="output-image svg">
						{@html output.data['image/svg+xml']}
					</div>
				{:else if output.data['text/html']}
					<div class="output-html">
						{@html getOutputText(output.data['text/html'])}
					</div>
				{:else if output.data['text/plain']}
					<div class="output-text">
						<pre>{getOutputText(output.data['text/plain'])}</pre>
					</div>
				{/if}
			{:else if output.output_type === 'error'}
				<div class="output-error">
					<div class="error-header">
						<span class="error-name">{output.ename}</span>: {output.evalue}
					</div>
					<pre class="error-traceback">{@html output.traceback.map(line => ansiToHtml(escapeHtml(line))).join('\n')}</pre>
				</div>
			{/if}
		{/each}
	</div>
{/if}

<style>
	.cell-outputs {
		background: var(--surface);
		overflow: hidden;
		min-width: 0;
	}

	/* Stream output (stdout/stderr) */
	.output-stream pre {
		margin: 0;
		padding: var(--space-md);
		font-family: var(--font-mono);
		font-size: var(--font-base); /* TEST: smaller to verify styles apply */
		font-weight: 500; /* Match CodeMirror */
		line-height: 1.5;
		white-space: pre-wrap;
		word-break: break-word;
		background: transparent;
		border: none;
		border-radius: 0;
		color: var(--text-muted);
	}

	.output-stream.stderr {
		background: var(--warning-bg);
	}

	.output-stream.stderr pre {
		color: var(--warning);
	}

	/* Image output */
	.output-image {
		padding: var(--space-md);
		display: flex;
		justify-content: center;
		background: var(--surface);
	}

	.output-image img {
		max-width: 100%;
		height: auto;
		border-radius: var(--radius-sm);
		background: transparent;
	}

	.output-image.svg {
		background: transparent;
		border-radius: var(--radius-sm);
		margin: var(--space-md);
		overflow: hidden;
	}

	.output-image.svg :global(svg) {
		max-width: 100%;
		height: auto;
		display: block;
	}

	/* HTML output - styled like docstring content */
	.output-html {
		padding: var(--space-md);
		overflow-x: auto;
		font-size: var(--font-base);
		line-height: 1.7;
		color: var(--text-muted);
	}

	/* Tables in HTML output - rounded outer border, inner cells use
	   single-line separators so border-radius isn't broken by
	   collapsed cell borders. */
	.output-html :global(table) {
		width: 100%;
		border-collapse: separate;
		border-spacing: 0;
		font-size: var(--font-base);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.output-html :global(th),
	.output-html :global(td) {
		padding: var(--space-xs) var(--space-sm);
		border: 0;
		border-bottom: 1px solid var(--border);
		text-align: left;
	}

	.output-html :global(th + th),
	.output-html :global(td + td) {
		border-left: 1px solid var(--border);
	}

	.output-html :global(tr:last-child td) {
		border-bottom: 0;
	}

	.output-html :global(th) {
		background: var(--surface-raised);
		font-weight: 600;
		color: var(--text-muted);
	}

	/* Plain text output */
	.output-text pre {
		margin: 0;
		padding: var(--space-md);
		font-family: var(--font-mono);
		font-size: var(--font-base);
		font-weight: 500; /* Match CodeMirror */
		line-height: 1.5;
		white-space: pre-wrap;
		word-break: break-word;
		background: transparent;
		border: none;
		border-radius: 0;
		color: var(--text-muted);
	}

	/* Error output */
	.output-error {
		background: var(--error-bg);
	}

	.error-header {
		padding: var(--space-sm) var(--space-md);
		font-family: var(--font-mono);
		font-size: var(--font-base);
		color: var(--error);
		font-weight: 600;
	}

	.error-name {
		color: var(--error);
	}

	.error-traceback {
		margin: 0;
		padding: var(--space-md);
		padding-top: 0;
		font-family: var(--font-mono);
		font-size: var(--font-base);
		line-height: 1.5;
		white-space: pre-wrap;
		word-break: break-word;
		color: var(--text-muted);
		background: transparent;
		border: none;
		border-radius: 0;
	}
</style>
