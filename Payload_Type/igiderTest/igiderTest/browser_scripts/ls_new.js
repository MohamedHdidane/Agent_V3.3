function(task, responses){
    if(task.status.includes("error")){
        const combined = responses.reduce((prev, cur) => {
            return prev + cur;
        }, "");
        return {'plaintext': combined};
    }
    
    try {
        const data = JSON.parse(responses[0]);
        
        if(data.hasOwnProperty("error")){
            return {'plaintext': data.error};
        }
        
        if(!data.hasOwnProperty("files")){
            return {'plaintext': responses[0]};
        }
        
        let output = "";
        
        // Create table header
        output += `<table class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Permissions</th>
                    <th>Modified</th>
                </tr>
            </thead>
            <tbody>`;
        
        // Process files
        for(const file of data.files){
            const fileType = file.is_file ? "File" : "Directory";
            const fileIcon = file.is_file ? "file" : "folder";
            const fileSizeFormatted = formatFileSize(file.size);
            const fileDate = new Date(file.modify_time * 1000).toLocaleString();
            
            // Create table row
            output += `
                <tr>
                    <td><i class="fas fa-${fileIcon}"></i> ${fileType}</td>
                    <td>${escapeHTML(file.name)}</td>
                    <td>${fileSizeFormatted}</td>
                    <td>${file.permissions.octal}</td>
                    <td>${fileDate}</td>
                </tr>`;
        }
        
        output += `</tbody></table>`;
        
        // Add parent path info
        if(data.parent_path){
            output = `<div class="alert alert-secondary">Current Directory: ${escapeHTML(data.parent_path)}</div>` + output;
        }
        
        return {
            'title': `Directory Listing: ${data.parent_path || "unknown"}`,
            'output': output
        };
    } catch(error) {
        return {'plaintext': `Error parsing response: ${error}\n\n${responses[0]}`};
    }
    
    // Helper function to format file size
    function formatFileSize(bytes) {
        if(bytes === 0) return '0 B';
        
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + units[i];
    }
    
    // Helper function to escape HTML
    function escapeHTML(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}