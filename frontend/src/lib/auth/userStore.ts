import { defineStore } from 'pinia';
import { whoami as fetchUserInfo } from './utils';
import type { UserInfo } from './utils';

type UserState = {
  token: string | null;
  userInfo: UserInfo | null;
  loading: boolean;
};

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: localStorage.getItem('token'),
    userInfo: null,
    loading: false,
  }),
  getters: {
    isLogin: (state) => !!state.token,
    username: (state) => state.userInfo?.username || '',
    avatarUrl: (state) => state.userInfo?.avatar_uri || '',
  },
  actions: {
    setToken(token: string) {
      localStorage.setItem('token', token);
      this.token = token;
    },
    async fetchUser() {
      if (!this.isLogin) {
        this.userInfo = null;
        return null;
      }
      this.loading = true;
      try {
        const data = await fetchUserInfo();
        if (!data) {
          this.logout();
          return null;
        }
        this.userInfo = data;
        return data;
      } catch (error) {
        this.logout();
        console.error('fetchUser failed:', error);
        return null;
      } finally {
        this.loading = false;
      }
    },
    logout() {
      localStorage.removeItem('token');
      this.token = null;
      this.userInfo = null;
    },
  },
});
