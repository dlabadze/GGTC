/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * External File Editor Client Action
 * Sends file to external editor silently without displaying any UI
 */
async function externalFileEditorAction(env, action) {
    const notification = env.services.notification;
    
    try {
        const params = action.params;
        
        if (!params) {
            throw new Error("Missing parameters");
        }

        const externalEditorUrl = params.external_editor_url || "http://localhost:4706/wordedit";
        
        // Prepare payload
        const payload = {
            Document: params.file_content, // Base64 encoded file
            fileName: params.file_name,
            CallbackURL: params.callback_url,
            token: params.token,
            db: params.db,
            login: params.login,
            // Note: External editor must send back: db, login, password, token, Document
        };

        console.log("Sending to external editor:", externalEditorUrl);
        console.log("Payload:", {
            fileName: payload.fileName,
            CallbackURL: payload.CallbackURL,
            token: payload.token,
            db: payload.db,
            login: payload.login,
            Document: payload.Document ? `${payload.Document.substring(0, 50)}...` : 'N/A'
        });

        // Make POST request to external editor
        const response = await fetch(externalEditorUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json; charset=utf-8",
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`External editor returned status: ${response.status}`);
        }

        const responseData = await response.json();
        console.log("External editor response:", responseData);

        // Show success notification
        notification.add("ფაილი გაიგზავნა რედაქტორში წარმატებით", {
            type: "success",
        });

    } catch (error) {
        console.error("Error calling external editor:", error);
        
        let errorMessage = error.message;
        if (error.message.includes("Failed to fetch")) {
            errorMessage = "გარე რედაქტორთან კავშირი ვერ დამყარდა. დარწმუნდით, რომ სერვისი გაშვებულია: http://localhost:4706";
        }
        
        notification.add(errorMessage, {
            type: "danger",
        });
    }
}

// Register the client action
registry.category("actions").add("external_file_editor", externalFileEditorAction);
