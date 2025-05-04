function(task, responses) {
    if (responses.length === 0) {
        return "<div class='alert alert-warning'>No response yet...</div>";
    }
    
    try {
        const response = JSON.parse(responses[0]);
        
        // Handle error responses
        if (response.status === "error" || response.result?.status === "error") {
            const errorMessage = response.message || response.result?.message || "Unknown error";
            return `<div class='alert alert-danger'>Error: ${errorMessage}</div>`;
        }
        
        // Extract results from the response
        const result = response.result || response;
        const files = result.files || [];
        const path = result.path || ".";
        
        // Build the table
        let output = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">Directory: ${path}</h5>
                </div>
                <div class="card-body p-0">
                    <table class="table table-striped table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Name</th>
                                <th>Size</th>
                                <th>Permissions</th>
                                <th>Last Modified</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        // Sort directories first, then files
        const sortedFiles = [...files].sort((a, b) => {
            if (a.is_dir !== b.is_dir) {
                return a.is_dir ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
        });
        
        // Add rows for each file/directory
        for (const file of sortedFiles) {
            const icon = file.is_dir ? 
                '<i class="fas fa-folder text-warning"></i>' : 
                '<i class="fas fa-file text-primary"></i>';
                
            const size = file.is_dir ? '-' : formatFileSize(file.size);
            
            output += `
                <tr>
                    <td>${icon}</td>
                    <td>${file.name}</td>
                    <td>${size}</td>
                    <td>${file.permissions}</td>
                    <td>${file.last_modified}</td>
                </tr>
            `;
        }
        
        output += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        return output;
    } catch (error) {
        return `<div class='alert alert-danger'>Error parsing response: ${error.message}</div>`;
    }
}

// Helper function to format file sizes
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
}
