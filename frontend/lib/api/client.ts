import axios from "axios"

export const apiClient = axios.create({
    // baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
    baseURL: "http://localhost:8000",
    timeout: 5000,
})
