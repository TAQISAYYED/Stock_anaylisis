import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000/api",
});

export const getSectors = () => API.get("/sectors/");
export const getStocks = (sectorId) => API.get(`/stocks/${sectorId}/`);
export const getAnalysis = (stockId) => API.get(`/analysis/${stockId}/`);