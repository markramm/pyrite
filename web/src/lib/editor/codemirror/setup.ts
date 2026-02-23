/** CodeMirror 6 base configuration */

import { autocompletion, closeBrackets } from '@codemirror/autocomplete';
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
import { markdown, markdownLanguage } from '@codemirror/lang-markdown';
import { bracketMatching, indentOnInput } from '@codemirror/language';
import { highlightSelectionMatches, searchKeymap } from '@codemirror/search';
import type { Extension } from '@codemirror/state';
import {
	EditorView,
	drawSelection,
	dropCursor,
	highlightActiveLine,
	highlightActiveLineGutter,
	keymap,
	lineNumbers
} from '@codemirror/view';
import { slashCommandCompletions } from './slash-commands';
import { darkTheme, lightTheme } from './theme';
import { wikilinkCompletions, wikilinkExtension } from './wikilinks';

export function createEditorExtensions(options: {
	dark?: boolean;
	onSave?: () => void;
	onChange?: (content: string) => void;
}): Extension[] {
	const { dark = true, onSave, onChange } = options;

	const saveKeymap = onSave
		? [
				{
					key: 'Mod-s',
					run: () => {
						onSave();
						return true;
					}
				}
			]
		: [];

	const extensions: Extension[] = [
		lineNumbers(),
		highlightActiveLineGutter(),
		highlightActiveLine(),
		drawSelection(),
		dropCursor(),
		indentOnInput(),
		bracketMatching(),
		closeBrackets(),
		autocompletion({
			override: [slashCommandCompletions, wikilinkCompletions],
			activateOnTyping: true
		}),
		highlightSelectionMatches(),
		history(),
		markdown({ base: markdownLanguage }),
		wikilinkExtension(),
		dark ? darkTheme : lightTheme,
		keymap.of([...saveKeymap, indentWithTab, ...defaultKeymap, ...historyKeymap, ...searchKeymap])
	];

	if (onChange) {
		extensions.push(
			EditorView.updateListener.of((update) => {
				if (update.docChanged) {
					onChange(update.state.doc.toString());
				}
			})
		);
	}

	return extensions;
}
