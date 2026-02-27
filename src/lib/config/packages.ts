// Centralized package configuration for PathSim Docs
// All package-specific content is defined here for dynamic page generation

export const external = {
	home: 'https://pathsim.org',
	view: 'https://view.pathsim.org',
	github: 'https://github.com/pathsim',
	pypi: 'https://pypi.org/project',
	conda: 'https://anaconda.org/conda-forge',
	sponsor: 'https://github.com/sponsors/milanofthe'
};

export type PackageId = 'pathsim' | 'chem' | 'vehicle';

export interface Feature {
	title: string;
	description: string;
}

export interface InstallOption {
	name: string;
	command: string;
	minVersion?: string; // Minimum version that supports this install method (e.g., "0.14.0")
}

export interface QuickStart {
	description: string;
	code: string;
	title?: string;
}

export interface ApiModule {
	name: string;
	description: string;
}

// Note: Examples are now loaded dynamically from manifest.json
// See src/lib/notebook/manifest.ts

export interface PackageConfig {
	id: PackageId;
	name: string;
	shortName: string;
	description: string;
	logo: string;

	// Links
	docs: string;
	api: string;
	examples: string | null;  // null if no examples
	pypi: string | null;  // null if not yet on PyPI
	conda: string | null;  // null if not on conda-forge
	github: string;

	// Content
	features: Feature[];
	installation: InstallOption[];  // empty if not installable yet
	quickstart: QuickStart | null;  // null if no quickstart

	// API page content
	apiModules: ApiModule[];
}

export const packages: Record<PackageId, PackageConfig> = {
	pathsim: {
		id: 'pathsim',
		name: 'PathSim',
		shortName: 'pathsim',
		description: 'A Python library for building and simulating continuous-time, discrete-time, and hybrid dynamical systems using a block-diagram approach.',
		logo: 'pathsim_logo.png',
		docs: 'pathsim',
		api: 'pathsim/api',
		examples: 'pathsim/examples',
		pypi: `${external.pypi}/pathsim`,
		conda: `${external.conda}/pathsim`,
		github: `${external.github}/pathsim`,
		features: [
			{ title: 'Block-based', description: 'Build systems by connecting reusable blocks' },
			{ title: '18+ Solvers', description: 'Explicit, implicit, and adaptive integrators' },
			{ title: 'Event Handling', description: 'Zero-crossing detection and scheduled events' },
			{ title: 'Hierarchical', description: 'Nest subsystems for modular designs' },
			{ title: 'Hot-swappable', description: 'Change blocks and solvers during simulation' },
			{ title: 'MIMO Support', description: 'Multiple input/output ports on all blocks' }
		],
		installation: [
			{ name: 'pip', command: 'pip install pathsim' },
			{ name: 'conda', command: 'conda install -c conda-forge pathsim', minVersion: '0.14.0' }
		],
		quickstart: {
			description: 'PathSim uses a block-diagram approach. Create blocks, connect them, and simulate.',
			code: `from pathsim import Simulation, Connection
from pathsim.blocks import Integrator, Amplifier, Scope

# Create blocks
integ = Integrator(1.0)   # Initial value x(0) = 1.0
amp = Amplifier(-0.5)     # Gain = -0.5
scope = Scope()           # Records the output

# Create connections
connections = [
    Connection(integ, amp, scope),  # integ -> amp, integ -> scope
    Connection(amp, integ)          # amp -> integ (feedback)
]

# Build and run simulation
sim = Simulation([integ, amp, scope], connections)
sim.run(10.0)

# Plot results
scope.plot()`,
			title: 'Example'
		},
		apiModules: [
			{ name: 'pathsim', description: 'Main module with Simulation and Connection classes' },
			{ name: 'pathsim.blocks', description: 'Block library (Integrator, Amplifier, Scope, etc.)' },
			{ name: 'pathsim.solvers', description: 'Numerical integrators' },
			{ name: 'pathsim.events', description: 'Event handling' }
		]
	},
	chem: {
		id: 'chem',
		name: 'PathSim-Chem',
		shortName: 'chem',
		description: 'Chemical engineering blocks for PathSim — IK-CAPE thermodynamic property correlations, activity coefficients, equations of state, and tritium processing.',
		logo: 'pathsim_chem_logo.png',
		docs: 'chem',
		api: 'chem/api',
		examples: 'chem/examples',
		pypi: `${external.pypi}/pathsim-chem`,
		conda: null,
		github: `${external.github}/pathsim-chem`,
		features: [
			{ title: 'IK-CAPE Standard', description: '50+ blocks implementing DECHEMA thermodynamic equations' },
			{ title: 'Property Correlations', description: 'Antoine, Wagner, DIPPR, and 13 more temperature correlations' },
			{ title: 'Activity Coefficients', description: 'NRTL, Wilson, UNIQUAC, and Flory-Huggins models' },
			{ title: 'Equations of State', description: 'Peng-Robinson and Soave-Redlich-Kwong cubic EoS' },
			{ title: 'Fugacity & Enthalpy', description: 'Fugacity coefficients, excess enthalpy, departure functions' },
			{ title: 'Tritium Processing', description: 'GLC columns, TCAP cascades, bubblers, and splitters' }
		],
		installation: [
			{ name: 'pip', command: 'pip install pathsim-chem' }
		],
		quickstart: {
			description: 'PathSim-Chem blocks follow the standard PathSim interface. Set inputs, call update, read outputs.',
			code: `from pathsim_chem.thermodynamics import Antoine

# Antoine vapor pressure correlation for water
antoine = Antoine(a0=23.2256, a1=3835.18, a2=-45.343)

# Evaluate at 100 °C (373.15 K)
antoine.inputs[0] = 373.15
antoine.update(None)
P_sat = antoine.outputs[0]  # ≈ 101325 Pa`,
			title: 'Example'
		},
		apiModules: [
			{ name: 'pathsim_chem.thermodynamics.correlations', description: '16 pure component property correlations' },
			{ name: 'pathsim_chem.thermodynamics.averages', description: '10 mixing rules for calculation of averages' },
			{ name: 'pathsim_chem.thermodynamics.activity_coefficients', description: 'NRTL, Wilson, UNIQUAC, Flory-Huggins' },
			{ name: 'pathsim_chem.thermodynamics.equations_of_state', description: 'Peng-Robinson, Soave-Redlich-Kwong' },
			{ name: 'pathsim_chem.thermodynamics.corrections', description: 'Poynting correction, Henry\'s law' },
			{ name: 'pathsim_chem.thermodynamics.fugacity_coefficients', description: 'RKS, PR, and virial fugacity coefficients' },
			{ name: 'pathsim_chem.thermodynamics.enthalpy', description: 'Excess enthalpy and enthalpy departure' },
			{ name: 'pathsim_chem.thermodynamics.reactions', description: 'Equilibrium constants, rate constants, power-law rates' },
			{ name: 'pathsim_chem.tritium', description: 'GLC, TCAP, bubbler, splitter blocks' }
		]
	},
	vehicle: {
		id: 'vehicle',
		name: 'PathSim-Vehicle',
		shortName: 'vehicle',
		description: 'Vehicle dynamics blocks for PathSim, including tire models, suspension systems, and powertrain components.',
		logo: 'pathsim_vehicle_logo.png',
		docs: 'vehicle',
		api: 'vehicle/api',
		examples: null,
		pypi: null,
		conda: null,
		github: `${external.github}/pathsim-vehicle`,
		features: [],
		installation: [],
		quickstart: null,
		apiModules: [
			{ name: 'pathsim_vehicle.tires', description: 'Pacejka magic formula, linear tire models' },
			{ name: 'pathsim_vehicle.suspension', description: 'Spring-damper systems' },
			{ name: 'pathsim_vehicle.powertrain', description: 'Engine, transmission models' },
			{ name: 'pathsim_vehicle.body', description: 'Multi-body vehicle dynamics' }
		]
	}
};

// Ordered list for tabs/navigation
export const packageOrder: PackageId[] = ['pathsim', 'chem', 'vehicle'];

// Sidebar navigation (auto-generated from package config)
export interface SidebarItem {
	title: string;
	path: string;
	icon?: string;
}

/**
 * Get sidebar navigation items for a package.
 * When version is provided, API and Examples paths are versioned.
 */
export function getSidebarItems(packageId: PackageId, version?: string): SidebarItem[] {
	const pkg = packages[packageId];
	const items: SidebarItem[] = [
		{ title: 'Overview', path: pkg.docs, icon: 'home' }
	];

	// Add versioned API path
	if (version) {
		items.push({ title: 'API Reference', path: `${packageId}/${version}/api`, icon: 'braces' });
	} else {
		items.push({ title: 'API Reference', path: pkg.api, icon: 'braces' });
	}

	// Add versioned examples path if package has examples
	if (pkg.examples) {
		if (version) {
			items.push({ title: 'Examples', path: `${packageId}/${version}/examples`, icon: 'play' });
		} else {
			items.push({ title: 'Examples', path: pkg.examples, icon: 'play' });
		}
	}

	return items;
}

// Navigation links
export const nav = {
	home: external.home,
	editor: external.view,
	github: external.github,
	sponsor: external.sponsor
};
