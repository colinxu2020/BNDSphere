import {
  getCurrentUserInfoApiV1UsersMeGet,
  getUserProfileApiV1UsersUserIdGet,
  updateUserProfileApiV1UsersMePatch,
} from '@/client';

export interface UserInfo {
  id: number;
  username: string;
  email: string | null;
  avatar_uri: string | null;
  description: string;
  role: string;
  created_at: string;
}

export interface UpdateMyProfilePayload {
  email?: string | null;
  avatar_uri?: string | null;
  description?: string | null;
}

export async function whoami() {
  try {
    const { data, error } = await getCurrentUserInfoApiV1UsersMeGet();

    if (error) {
      // 根据实际响应结构判断错误
      console.log('User fetch failed', error);
      if (typeof error === 'object' && error !== null && 'detail' in error) {
        console.log('未授权，请重新登录');
      }
      return null;
    }

    if (data) {
      localStorage.setItem('userInfo', JSON.stringify(data));
      return data as UserInfo;
    }
    return null;
  } catch (err) {
    console.error('请求发生未知错误：', err);
    return null;
  }
}

export async function checkAuth() {
  const res = await whoami();
  return res !== null;
}

export async function getUserById(userId: number) {
  const { data, error } = await getUserProfileApiV1UsersUserIdGet({
    path: { user_id: userId },
  });
  if (error) throw new Error(typeof error === 'string' ? error : 'Failed to fetch user');
  return data as UserInfo;
}

export async function updateMyProfile(payload: UpdateMyProfilePayload) {
  const { data, error } = await updateUserProfileApiV1UsersMePatch({
    body: payload,
  });

  if (error) throw new Error(typeof error === 'string' ? error : 'Failed to update profile');
  if (data) {
    localStorage.setItem('userInfo', JSON.stringify(data));
  }
  return data as UserInfo;
}
