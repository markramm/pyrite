/** UI state: theme, sidebar, toasts */

export interface Toast {
	id: number;
	message: string;
	type: 'success' | 'error' | 'info';
}

let nextToastId = 0;

class UIStore {
	theme = $state<'light' | 'dark'>('dark');
	sidebarOpen = $state(true);
	backlinksPanelOpen = $state(false);
	outlinePanelOpen = $state(false);
	versionHistoryPanelOpen = $state(false);
	chatPanelOpen = $state(false);
	localGraphPanelOpen = $state(false);
	editorMode = $state<'source' | 'wysiwyg'>('source');
	toasts = $state<Toast[]>([]);

	constructor() {
		// Load theme from localStorage on init (browser only)
		if (typeof window !== 'undefined') {
			const saved = localStorage.getItem('pyrite-theme');
			if (saved === 'light' || saved === 'dark') {
				this.theme = saved;
			}
			this.applyTheme();
			// Start sidebar closed on mobile, open on desktop
			this.sidebarOpen = window.innerWidth >= 1024;
		}
	}

	toggleTheme() {
		this.theme = this.theme === 'dark' ? 'light' : 'dark';
		if (typeof window !== 'undefined') {
			localStorage.setItem('pyrite-theme', this.theme);
			this.applyTheme();
		}
	}

	private applyTheme() {
		document.documentElement.classList.toggle('dark', this.theme === 'dark');
	}

	toggleBacklinksPanel() {
		this.backlinksPanelOpen = !this.backlinksPanelOpen;
	}

	toggleOutlinePanel() {
		this.outlinePanelOpen = !this.outlinePanelOpen;
	}

	toggleVersionHistoryPanel() {
		this.versionHistoryPanelOpen = !this.versionHistoryPanelOpen;
	}

	toggleSidebar() {
		this.sidebarOpen = !this.sidebarOpen;
	}

	toggleChatPanel() {
		this.chatPanelOpen = !this.chatPanelOpen;
	}

	toggleLocalGraphPanel() {
		this.localGraphPanelOpen = !this.localGraphPanelOpen;
	}

	toggleEditorMode() {
		this.editorMode = this.editorMode === 'source' ? 'wysiwyg' : 'source';
	}

	toast(message: string, type: Toast['type'] = 'info') {
		const id = nextToastId++;
		this.toasts = [...this.toasts, { id, message, type }];
		setTimeout(() => {
			this.toasts = this.toasts.filter((t) => t.id !== id);
		}, 3000);
	}
}

export const uiStore = new UIStore();
