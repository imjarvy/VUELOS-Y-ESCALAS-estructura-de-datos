const BASE_URL = "http://localhost:5000";

/**
 * 
 * puente entre el frontend y el backend hecho con Flask.
 * Procesa la respuesta estándar de la API
 */
async function handleResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const rawBody = isJson ? await response.json().catch(() => null) : await response.text().catch(() => "");

    if (!response.ok) {
        const message = rawBody && typeof rawBody === "object"
            ? rawBody.error || rawBody.message || JSON.stringify(rawBody)
            : rawBody || response.statusText || `HTTP ${response.status}`;
        throw new Error(message);
    }

    if (rawBody && typeof rawBody === "object") {
        if (rawBody.error) {
            throw new Error(rawBody.message || rawBody.error || "Error en la petición");
        }
        return rawBody.data || rawBody;
    }

    return rawBody;
}

/**
 * GET
 */
export async function apiGet(url) {
    try {
        const response = await fetch(`${BASE_URL}${url}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        });

        return await handleResponse(response);

    } catch (error) {
        console.error("GET Error:", error.message);
        throw error;
    }
}

/**
 * POST
 */
export async function apiPost(url, data) {
    try {
        const response = await fetch(`${BASE_URL}${url}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        return await handleResponse(response);

    } catch (error) {
        console.error("POST Error:", error.message);
        throw error;
    }
}

export async function apiPostFormData(url, formData) {
    try {
        const response = await fetch(`${BASE_URL}${url}`, {
            method: "POST",
            body: formData 
        });

        return await handleResponse(response);

    } catch (error) {
        console.error("POST Form Data Error:", error.message);
        throw error;
    }
}

/**
 * PUT
 */
export async function apiPut(url, data) {
    try {
        const response = await fetch(`${BASE_URL}${url}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        return await handleResponse(response);

    } catch (error) {
        console.error("PUT Error:", error.message);
        throw error;
    }
}

/**
 * DELETE
 */
export async function apiDelete(url) {
    try {
        const response = await fetch(`${BASE_URL}${url}`, {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            }
        });

        return await handleResponse(response);

    } catch (error) {
        console.error("DELETE Error:", error.message);
        throw error;
    }
}