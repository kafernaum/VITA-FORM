import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vf_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      // token expired
      const path = window.location.pathname;
      if (!path.startsWith("/auth") && path !== "/") {
        localStorage.removeItem("vf_token");
        localStorage.removeItem("vf_user");
      }
    }
    return Promise.reject(err);
  }
);
