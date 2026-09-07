
export * from './api/types';
export * from './api/client';
import { profilesApi } from './api/profiles';
import { campaignsApi } from './api/campaigns';
import { activityApi } from './api/activity';
import { systemApi } from './api/system';

export { profilesApi, campaignsApi, activityApi, systemApi };

export const api = {
  ...profilesApi,
  ...campaignsApi,
  ...activityApi,
  ...systemApi,
  profiles: profilesApi,
  campaigns: campaignsApi,
  activity: activityApi,
  system: systemApi,
};
