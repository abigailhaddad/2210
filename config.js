// Configuration file for USA Jobs 2210 Data Explorer
window.DATASET_CONFIG = {
    title: 'USAJobs 2210 Positions',
    subtitle: 'IT Management Series Positions',
    datasetName: 'USAJobs2210',
    keyField: 'controlNumber',
    
    // Theme options
    theme: {
        colorScheme: 'slate',
        buttonStyle: 'flat',
        cardStyle: 'minimal'
    },
    
    fields: [
        { 
            key: 'controlNumber',           
            title: 'ID',           
            visible: false 
        },
        { 
            key: 'positionTitle',         
            title: 'Position Title',         
            filter: 'text', 
            visible: true 
        },
        { 
            key: 'agencyName',        
            title: 'Agency',        
            filter: 'select', 
            visible: true 
        },
        { 
            key: 'departmentName',   
            title: 'Department',   
            filter: 'select', 
            visible: true 
        },
        { 
            key: 'payScale',        
            title: 'Grade',        
            filter: 'select', 
            visible: true 
        },
        {
            key: 'locations',
            title: 'Location',
            filter: 'select',
            visible: true
        },
        { 
            key: 'salaryRange',       
            title: 'Salary Range',       
            format: 'text', 
            filter: 'text',
            visible: true,
            transform: (value) => {
                // Format salary range as currency
                const parts = value.split(' - ');
                if (parts.length === 2) {
                    const min = parseFloat(parts[0]);
                    const max = parseFloat(parts[1]);
                    return `$${min.toLocaleString()} - $${max.toLocaleString()}`;
                }
                return value;
            }
        },
        { 
            key: 'workSchedule',     
            title: 'Work Schedule',     
            filter: 'select', 
            visible: false 
        },
        { 
            key: 'openDate',       
            title: 'Posted Date',    
            format: 'date', 
            filter: 'date',
            visible: false 
        },
        { 
            key: 'closeDate',       
            title: 'Closing Date',    
            format: 'date', 
            filter: 'date',
            visible: false 
        },
        {              
            key: 'hiringPaths',                  
            title: 'Hiring Path',                
            filter: 'text',
            format: 'text',              
            visible: false,
            transform: (value) => {
                // Split by commas to create a list
                return value.split(', ').map(path => path.trim());
            }
        },
        { 
            key: 'announcementNumber',        
            title: 'Announcement #',        
            filter: 'text', 
            visible: false 
        },
        { 
            key: 'jobRequirementsText',        
            title: 'Requirements',        
            filter: 'text', 
            visible: false 
        },
        { 
            key: 'jobDutiesText',        
            title: 'Duties',        
            filter: 'text', 
            visible: false 
        },
        {
            key: 'teleworkEligible',
            title: 'Telework Eligible',
            filter: 'select',
            visible: false,
            transform: (value) => value === 'Y' ? 'Yes' : 'No'
        }
    ],
    
    stats: [
        { 
            key: 'total',        
            label: 'Total Positions',    
            type: 'count' 
        },
        { 
            key: 'agencyName',   
            label: 'Agencies',      
            type: 'unique' 
        },
    ],
    
    // Additional processing function to prepare data
    preProcessData: function(data) {
        return data.map(item => {
            // Any additional transformations needed
            return item;
        });
    }
};