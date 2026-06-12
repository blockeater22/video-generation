import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, withCredentials: true });

// Attach bearer token from localStorage
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const setToken = (t) => {
  if (t) localStorage.setItem("access_token", t);
  else localStorage.removeItem("access_token");
};

export const api = {
  // auth
  register: (body) => client.post("/auth/register", body).then((r) => r.data),
  login: (body) => client.post("/auth/login", body).then((r) => r.data),
  logout: () => client.post("/auth/logout").then((r) => r.data),
  me: () => client.get("/auth/me").then((r) => r.data),
  forgotPassword: (body) => client.post("/auth/forgot-password", body).then((r) => r.data),
  resetPassword: (body) => client.post("/auth/reset-password", body).then((r) => r.data),

  // org / dashboard / team
  org: () => client.get("/org").then((r) => r.data),
  updateOrg: (body) => client.patch("/org", body).then((r) => r.data),
  dashboardStats: () => client.get("/dashboard/stats").then((r) => r.data),
  listMembers: () => client.get("/members").then((r) => r.data),
  listInvitations: () => client.get("/invitations").then((r) => r.data),
  createInvitation: (body) => client.post("/invitations", body).then((r) => r.data),
  deleteInvitation: (id) => client.delete(`/invitations/${id}`),

  // projects
  listProjects: () => client.get("/projects").then((r) => r.data),
  createProject: (body) => client.post("/projects", body).then((r) => r.data),
  deleteProject: (id) => client.delete(`/projects/${id}`),

  // avatars
  listAvatars: () => client.get("/avatars").then((r) => r.data),
  createAvatar: (body) => client.post("/avatars", body).then((r) => r.data),
  deleteAvatar: (id) => client.delete(`/avatars/${id}`),

  // voices
  listVoices: () => client.get("/voices").then((r) => r.data),
  createVoice: (body) => client.post("/voices", body).then((r) => r.data),
  deleteVoice: (id) => client.delete(`/voices/${id}`),

  // videos
  listVideos: (params = {}) => client.get("/videos", { params }).then((r) => r.data),
  getVideo: (id) => client.get(`/videos/${id}`).then((r) => r.data),
  createVideo: (body) => client.post("/videos", body).then((r) => r.data),
  updateVideo: (id, body) => client.patch(`/videos/${id}`, body).then((r) => r.data),
  deleteVideo: (id) => client.delete(`/videos/${id}`),
  retryVideo: (id) => client.post(`/videos/${id}/retry`).then((r) => r.data),

  // api keys
  listApiKeys: () => client.get("/api-keys").then((r) => r.data),
  createApiKey: (body) => client.post("/api-keys", body).then((r) => r.data),
  deleteApiKey: (id) => client.delete(`/api-keys/${id}`),

  // webhooks
  listWebhooks: () => client.get("/webhooks").then((r) => r.data),
  createWebhook: (body) => client.post("/webhooks", body).then((r) => r.data),
  deleteWebhook: (id) => client.delete(`/webhooks/${id}`),
  webhookDeliveries: (id) => client.get(`/webhooks/${id}/deliveries`).then((r) => r.data),
  testWebhook: (id) => client.post(`/webhooks/${id}/test`).then((r) => r.data),

  // billing
  billingPlans: () => client.get("/billing/plans").then((r) => r.data),
  billingCheckout: (body) => client.post("/billing/checkout", body).then((r) => r.data),
  billingStatus: (sid) => client.get(`/billing/status/${sid}`).then((r) => r.data),
};

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => (e?.msg ? e.msg : JSON.stringify(e))).join(" ");
  if (detail?.msg) return detail.msg;
  return String(detail);
}

export default api;
