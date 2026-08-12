/** 
 * Represents an authenticated user in the system.
 */
export type AuthUser = {
  id: string;
  username: string;
  email: string;
  companyName?: string;
};

export type LoginPayload = {
  identifier: string;
  password: string;
  remember: boolean;
};

export type RegisterPayload = {
  username: string;
  email: string;
  password: string;
  companyName?: string;
};
