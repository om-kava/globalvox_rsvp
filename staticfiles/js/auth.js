/**
 * GlobalVox RSVP — Authentication & Token Client (Vanilla JS)
 * Handles client-side boundary validation, JWT token storage, and authenticated API requests.
 */

const Auth = {
    ACCESS_TOKEN_KEY: 'gv_access_token',
    REFRESH_TOKEN_KEY: 'gv_refresh_token',
    USER_KEY: 'gv_user_profile',

    /**
     * Client-side pre-flight validation rules (Defense in Depth)
     */
    validateCredentials(username, password) {
        const errors = [];
        const cleanUser = (username || '').trim();

        if (!cleanUser) {
            errors.push('Username cannot be blank.');
        } else if (cleanUser.length > 150) {
            errors.push('Username cannot exceed 150 characters.');
        }

        if (!password) {
            errors.push('Password cannot be blank.');
        } else if (password.length > 128) {
            errors.push('Password cannot exceed 128 characters.');
        }

        return {
            isValid: errors.length === 0,
            errors,
            cleanUser
        };
    },

    /**
     * Authenticate user with backend and store tokens
     */
    async login(username, password) {
        const validation = this.validateCredentials(username, password);
        if (!validation.isValid) {
            throw new Error(validation.errors.join(' '));
        }

        const response = await fetch('/api/auth/login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: validation.cleanUser,
                password: password
            })
        });

        const data = await response.json();
        if (!response.ok) {
            const errorMsg = data.detail || (data.username && data.username[0]) || (data.password && data.password[0]) || 'Login failed.';
            throw new Error(errorMsg);
        }

        // Store tokens & user profile
        localStorage.setItem(this.ACCESS_TOKEN_KEY, data.access);
        localStorage.setItem(this.REFRESH_TOKEN_KEY, data.refresh);
        localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));

        return data;
    },

    /**
     * Get active access token
     */
    getAccessToken() {
        return localStorage.getItem(this.ACCESS_TOKEN_KEY);
    },

    /**
     * Get active refresh token
     */
    getRefreshToken() {
        return localStorage.getItem(this.REFRESH_TOKEN_KEY);
    },

    /**
     * Get cached user profile
     */
    getUser() {
        const userStr = localStorage.getItem(this.USER_KEY);
        try {
            return userStr ? JSON.parse(userStr) : null;
        } catch {
            return null;
        }
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.getAccessToken();
    },

    /**
     * Refresh the JWT access token using the stored refresh token
     */
    async refreshAccessToken() {
        const refresh = this.getRefreshToken();
        if (!refresh) {
            this.logout();
            return null;
        }

        try {
            const response = await fetch('/api/auth/refresh/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh })
            });

            if (!response.ok) {
                this.logout();
                return null;
            }

            const data = await response.json();
            localStorage.setItem(this.ACCESS_TOKEN_KEY, data.access);
            return data.access;
        } catch (e) {
            this.logout();
            return null;
        }
    },

    /**
     * Authenticated fetch wrapper with automatic JWT Bearer header and token renewal
     */
    async authFetch(url, options = {}) {
        let token = this.getAccessToken();
        if (!token) {
            throw new Error('Unauthenticated');
        }

        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${token}`;

        let response = await fetch(url, options);

        // If access token expired, try refreshing once
        if (response.status === 401) {
            const newToken = await this.refreshAccessToken();
            if (newToken) {
                options.headers['Authorization'] = `Bearer ${newToken}`;
                response = await fetch(url, options);
            }
        }

        return response;
    },

    /**
     * Log out, invalidate tokens, and clear storage
     */
    async logout() {
        const refresh = this.getRefreshToken();
        const token = this.getAccessToken();

        try {
            await fetch('/api/auth/logout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ refresh: refresh || '' })
            });
        } catch (e) {
            // Ignore network errors during logout
        } finally {
            localStorage.removeItem(this.ACCESS_TOKEN_KEY);
            localStorage.removeItem(this.REFRESH_TOKEN_KEY);
            localStorage.removeItem(this.USER_KEY);
        }
    }
};

window.Auth = Auth;
