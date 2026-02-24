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
	toasts = $state<Toast[]>([]);

	constructor() {
		// Load theme from localStorage on init (browser only)
		if (typeof window !== 'undefined') {
			const saved = localStorage.getItem('pyrite-theme');
			if (saved === 'light' || saved === 'dark') {
				this.theme = saved;
			}
			this.applyTheme();
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

	toggleSidebar() {
		this.sidebarOpen = !this.sidebarOpen;
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
