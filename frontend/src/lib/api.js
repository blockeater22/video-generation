import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API });

export const api = {
  org: () => client.get("/org").then((r) => r.data),
  dashboardStats: () => client.get("/dashboard/stats").then((r) => r.data),

  listProjects: () => client.get("/projects").then((r) => r.data),
  createProject: (body) => client.post("/projects", body).then((r) => r.data),
  deleteProject: (id) => client.delete(`/projects/${id}`),

  listAvatars: () => client.get("/avatars").then((r) => r.data),
  createAvatar: (body) => client.post("/avatars", body).then((r) => r.data),
  deleteAvatar: (id) => client.delete(`/avatars/${id}`),

  listVoices: () => client.get("/voices").then((r) => r.data),
  createVoice: (body) => client.post("/voices", body).then((r) => r.data),
  deleteVoice: (id) => client.delete(`/voices/${id}`),

  listVideos: (params = {}) => client.get("/videos", { params }).then((r) => r.data),
  getVideo: (id) => client.get(`/videos/${id}`).then((r) => r.data),
  createVideo: (body) => client.post("/videos", body).then((r) => r.data),
  updateVideo: (id, body) => client.patch(`/videos/${id}`, body).then((r) => r.data),
  deleteVideo: (id) => client.delete(`/videos/${id}`),
  retryVideo: (id) => client.post(`/videos/${id}/retry`).then((r) => r.data),
};

export default api;
