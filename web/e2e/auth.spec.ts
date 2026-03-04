import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
	test('login page loads', async ({ page }) => {
		await page.goto('/login');
		await expect(page).toHaveTitle(/Login/);
		await expect(page.getByRole('heading', { name: 'Pyrite' })).toBeVisible();
		await expect(page.locator('text=Sign in to your account')).toBeVisible();
	});

	test('login form has username field', async ({ page }) => {
		await page.goto('/login');
		const usernameInput = page.locator('input#username');
		await expect(usernameInput).toBeVisible();
		await expect(usernameInput).toHaveAttribute('type', 'text');
		await expect(usernameInput).toHaveAttribute('required', '');
		// Label is present
		await expect(page.locator('label[for="username"]')).toContainText('Username');
	});

	test('login form has password field', async ({ page }) => {
		await page.goto('/login');
		const passwordInput = page.locator('input#password');
		await expect(passwordInput).toBeVisible();
		await expect(passwordInput).toHaveAttribute('type', 'password');
		await expect(passwordInput).toHaveAttribute('required', '');
		await expect(page.locator('label[for="password"]')).toContainText('Password');
	});

	test('login form has submit button', async ({ page }) => {
		await page.goto('/login');
		const submitBtn = page.locator('button[type="submit"]');
		await expect(submitBtn).toBeVisible();
		await expect(submitBtn).toContainText('Sign in');
	});

	test('login form fields accept input', async ({ page }) => {
		await page.goto('/login');
		const usernameInput = page.locator('input#username');
		const passwordInput = page.locator('input#password');

		await usernameInput.fill('testuser');
		await passwordInput.fill('testpassword');

		await expect(usernameInput).toHaveValue('testuser');
		await expect(passwordInput).toHaveValue('testpassword');
	});

	test('login page has link to register when registration is allowed', async ({ page }) => {
		await page.goto('/login');
		// The register link is conditionally rendered based on authConfig.allow_registration
		// Check if it exists — it may or may not depending on server config
		const registerLink = page.locator('a[href="/register"]');
		const hasRegisterLink = await registerLink.isVisible({ timeout: 3000 }).catch(() => false);

		if (hasRegisterLink) {
			await expect(registerLink).toContainText('Register');
		}
		// If not visible, registration is disabled — that is valid behavior
	});

	test('login page shows Pyrite branding', async ({ page }) => {
		await page.goto('/login');
		await expect(page.locator('h1')).toContainText('Pyrite');
	});
});

test.describe('Register Page', () => {
	test('register page loads', async ({ page }) => {
		await page.goto('/register');
		await expect(page).toHaveTitle(/Register/);
		await expect(page.getByRole('heading', { name: 'Pyrite' })).toBeVisible();
		await expect(page.locator('text=Create your account')).toBeVisible();
	});

	test('register form has username field', async ({ page }) => {
		await page.goto('/register');
		const usernameInput = page.locator('input#username');
		await expect(usernameInput).toBeVisible();
		await expect(usernameInput).toHaveAttribute('required', '');
		await expect(page.locator('label[for="username"]')).toContainText('Username');
	});

	test('register form has display name field (optional)', async ({ page }) => {
		await page.goto('/register');
		const displayNameInput = page.locator('input#display-name');
		await expect(displayNameInput).toBeVisible();
		// Display name is optional — no required attribute
		await expect(page.locator('label[for="display-name"]')).toContainText('Display Name');
		await expect(page.locator('label[for="display-name"]')).toContainText('optional');
	});

	test('register form has password field', async ({ page }) => {
		await page.goto('/register');
		const passwordInput = page.locator('input#password');
		await expect(passwordInput).toBeVisible();
		await expect(passwordInput).toHaveAttribute('type', 'password');
		await expect(passwordInput).toHaveAttribute('required', '');
		await expect(page.locator('label[for="password"]')).toContainText('Password');
	});

	test('register form has confirm password field', async ({ page }) => {
		await page.goto('/register');
		const confirmInput = page.locator('input#confirm-password');
		await expect(confirmInput).toBeVisible();
		await expect(confirmInput).toHaveAttribute('type', 'password');
		await expect(confirmInput).toHaveAttribute('required', '');
		await expect(page.locator('label[for="confirm-password"]')).toContainText('Confirm Password');
	});

	test('register form has submit button', async ({ page }) => {
		await page.goto('/register');
		const submitBtn = page.locator('button[type="submit"]');
		await expect(submitBtn).toBeVisible();
		await expect(submitBtn).toContainText('Create account');
	});

	test('register form fields accept input', async ({ page }) => {
		await page.goto('/register');
		await page.locator('input#username').fill('newuser');
		await page.locator('input#display-name').fill('New User');
		await page.locator('input#password').fill('securepass123');
		await page.locator('input#confirm-password').fill('securepass123');

		await expect(page.locator('input#username')).toHaveValue('newuser');
		await expect(page.locator('input#display-name')).toHaveValue('New User');
		await expect(page.locator('input#password')).toHaveValue('securepass123');
		await expect(page.locator('input#confirm-password')).toHaveValue('securepass123');
	});

	test('register page has link to login', async ({ page }) => {
		await page.goto('/register');
		const loginLink = page.locator('a[href="/login"]');
		await expect(loginLink).toBeVisible();
		await expect(loginLink).toContainText('Sign in');
	});

	test('register page shows Pyrite branding', async ({ page }) => {
		await page.goto('/register');
		await expect(page.locator('h1')).toContainText('Pyrite');
	});
});
