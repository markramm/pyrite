declare module 'cytoscape-cose-bilkent' {
	// Cytoscape extension — registers itself via cytoscape.use(). No public API.
	const plugin: (cy: unknown) => void;
	export default plugin;
}
