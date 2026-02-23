/**
 * CodeMirror 6 extension for slash command support.
 *
 * Provides a Notion-style "/" menu that appears when the user types "/"
 * at the start of a line or after whitespace. Uses CodeMirror's built-in
 * autocomplete infrastructure.
 */

import type { Completion, CompletionContext, CompletionResult } from '@codemirror/autocomplete';
import { EditorView } from '@codemirror/view';

interface SlashCommand {
	label: string;
	keyword: string;
	description: string;
	section: string;
	apply: string | ((view: EditorView, completion: Completion, from: number, to: number) => void);
}

const SLASH_COMMANDS: SlashCommand[] = [
	// Headings
	{
		label: 'Heading 1',
		keyword: 'heading1',
		description: 'Large heading',
		section: 'Headings',
		apply: '# '
	},
	{
		label: 'Heading 2',
		keyword: 'heading2',
		description: 'Medium heading',
		section: 'Headings',
		apply: '## '
	},
	{
		label: 'Heading 3',
		keyword: 'heading3',
		description: 'Small heading',
		section: 'Headings',
		apply: '### '
	},

	// Callouts
	{
		label: 'Callout',
		keyword: 'callout',
		description: 'Info callout block',
		section: 'Blocks',
		apply: '> [!info]\n> '
	},
	{
		label: 'Warning',
		keyword: 'warning',
		description: 'Warning callout',
		section: 'Blocks',
		apply: '> [!warning]\n> '
	},
	{
		label: 'Tip',
		keyword: 'tip',
		description: 'Tip callout',
		section: 'Blocks',
		apply: '> [!tip]\n> '
	},

	// Code
	{
		label: 'Code Block',
		keyword: 'code',
		description: 'Fenced code block',
		section: 'Blocks',
		apply: (view: EditorView, _completion: Completion, from: number, to: number) => {
			const insert = '```\n\n```';
			view.dispatch({
				changes: { from, to, insert },
				selection: { anchor: from + 4 }
			});
		}
	},

	// Table
	{
		label: 'Table',
		keyword: 'table',
		description: 'Markdown table',
		section: 'Blocks',
		apply: (view: EditorView, _completion: Completion, from: number, to: number) => {
			const insert = '| Header | Header |\n| --- | --- |\n|  |  |';
			view.dispatch({
				changes: { from, to, insert },
				// Place cursor inside first data cell (after "| ")
				selection: { anchor: from + insert.indexOf('|  |') + 2 }
			});
		}
	},

	// Links
	{
		label: 'Wikilink',
		keyword: 'link',
		description: 'Insert wikilink',
		section: 'Inline',
		apply: '[['
	},

	// Date
	{
		label: "Today's Date",
		keyword: 'date',
		description: 'Current date (YYYY-MM-DD)',
		section: 'Inline',
		apply: (view: EditorView, _completion: Completion, from: number, to: number) => {
			const date = new Date().toISOString().split('T')[0];
			view.dispatch({
				changes: { from, to, insert: date }
			});
		}
	},

	// Divider
	{
		label: 'Divider',
		keyword: 'divider',
		description: 'Horizontal rule',
		section: 'Blocks',
		apply: '---\n'
	},

	// Task
	{
		label: 'Task List',
		keyword: 'todo',
		description: 'Checkbox list item',
		section: 'Lists',
		apply: '- [ ] '
	},

	// Quote
	{
		label: 'Blockquote',
		keyword: 'quote',
		description: 'Quote block',
		section: 'Blocks',
		apply: '> '
	}
];

/**
 * Autocomplete source for slash commands.
 * Triggers when "/" is typed at the start of a line or after whitespace.
 */
export function slashCommandCompletions(context: CompletionContext): CompletionResult | null {
	const line = context.state.doc.lineAt(context.pos);
	const textBefore = line.text.slice(0, context.pos - line.from);

	// Match "/" at line start or after whitespace
	const match = textBefore.match(/(?:^|\s)(\/\w*)$/);
	if (!match) return null;

	const slashStart = context.pos - match[1].length;
	const filter = match[1].slice(1).toLowerCase();

	const options: Completion[] = SLASH_COMMANDS.filter(
		(cmd) =>
			cmd.keyword.includes(filter) ||
			cmd.label.toLowerCase().includes(filter) ||
			cmd.description.toLowerCase().includes(filter)
	).map((cmd) => ({
		label: '/' + cmd.keyword,
		displayLabel: cmd.label,
		detail: cmd.description,
		section: cmd.section,
		type: 'keyword',
		boost: cmd.keyword.startsWith(filter) ? 1 : 0,
		apply: cmd.apply
	}));

	if (options.length === 0) return null;

	return {
		from: slashStart,
		to: context.pos,
		options,
		filter: false
	};
}
