const BASE_URL = "http://localhost:5000";

/**
 * 
 * puente entre el frontend y el backend hecho con Flask.
 * Procesa la respuesta estándar de la API
 */
async function handleResponse(response) {
    const result = await response.json();

    if (result.error) {
        throw new Error(result.message || "Error en la petición");
    }

    return result.data || result;
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