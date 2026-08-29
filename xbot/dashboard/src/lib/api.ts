
export * from './api/types';
export * from './api/client';
import { profilesApi } from './api/profiles';
import { campaignsApi } from './api/campaigns';
import { activityApi } from './api/activity';
import { systemApi } from './api/system';

export const api = {
  ...profilesApi,
  ...campaignsApi,
  ...activityApi,
  ...systemApi,
};
