/** Dark and light CodeMirror themes */

import { EditorView } from '@codemirror/view';

export const darkTheme = EditorView.theme(
	{
		'&': {
			backgroundColor: '#18181b',
			color: '#d4d4d8'
		},
		'.cm-content': {
			caretColor: '#60a5fa',
			fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
			fontSize: '14px',
			lineHeight: '1.6'
		},
		'.cm-cursor': {
			borderLeftColor: '#60a5fa'
		},
		'.cm-selectionBackground': {
			backgroundColor: '#2563eb33'
		},
		'&.cm-focused .cm-selectionBackground': {
			backgroundColor: '#2563eb44'
		},
		'.cm-activeLine': {
			backgroundColor: '#27272a'
		},
		'.cm-gutters': {
			backgroundColor: '#18181b',
			color: '#52525b',
			border: 'none'
		},
		'.cm-activeLineGutter': {
			backgroundColor: '#27272a'
		}
	},
	{ dark: true }
);

export const lightTheme = EditorView.theme(
	{
		'&': {
			backgroundColor: '#ffffff',
			color: '#18181b'
		},
		'.cm-content': {
			caretColor: '#2563eb',
			fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
			fontSize: '14px',
			lineHeight: '1.6'
		},
		'.cm-cursor': {
			borderLeftColor: '#2563eb'
		},
		'.cm-selectionBackground': {
			backgroundColor: '#2563eb22'
		},
		'&.cm-focused .cm-selectionBackground': {
			backgroundColor: '#2563eb33'
		},
		'.cm-activeLine': {
			backgroundColor: '#f4f4f5'
		},
		'.cm-gutters': {
			backgroundColor: '#ffffff',
			color: '#a1a1aa',
			border: 'none'
		},
		'.cm-activeLineGutter': {
			backgroundColor: '#f4f4f5'
		}
	},
	{ dark: false }
);
