
export const agents = [
    // HR Agents
    {
        id: 'hr-1',
        title: 'Employee Onboarding Assistant',
        description: 'Streamline the onboarding process by automating document collection, equipment requests, and training schedules.',
        industry: 'HR',
        function: 'HR',
        useCase: 'Onboarding',
        agentType: 'Process Automation',
        integrations: ['slack', 'workday', 'gmail'],
        tags: ['HR', 'Onboarding']
    },
    {
        id: 'hr-2',
        title: 'Policy Q&A Bot',
        description: 'Instant answers to employee questions about company policies, benefits, and holidays.',
        industry: 'HR',
        function: 'HR',
        useCase: 'Employee Support',
        agentType: 'Conversational',
        integrations: ['teams', 'sharepoint'],
        tags: ['HR', 'Support']
    },

    // Sales Agents
    {
        id: 'sales-1',
        title: 'Pre-Meeting Prep Automation',
        description: 'Integrate with google calendar to summarize previous emails and prepare meeting briefs.',
        industry: 'Technology',
        function: 'Sales',
        useCase: 'Meeting Prep',
        agentType: 'Assistant',
        integrations: ['gmail', 'calendar', 'salesforce'],
        tags: ['Sales', 'Productivity'],
        featured: true
    },
    {
        id: 'sales-2',
        title: 'Lead Enrichment Agent',
        description: 'Automatically enrich lead data from LinkedIn and clearbit to update CRM records.',
        industry: 'Sales',
        function: 'Sales',
        useCase: 'Lead Gen',
        agentType: 'Data Processing',
        integrations: ['hubspot', 'linkedin'],
        tags: ['Sales', 'CRM']
    },

    // Support Agents
    {
        id: 'supp-1',
        title: 'Support Ticket Categorizer',
        description: 'Automatically categorizes and tags tickets in ITSM for faster routing and resolution.',
        industry: 'Technology',
        function: 'Customer Support',
        useCase: 'Ticket Management',
        agentType: 'Classification',
        integrations: ['zendesk', 'jira'],
        tags: ['Support', 'ITSM'],
        featured: true
    },
    {
        id: 'supp-2',
        title: 'Escalation Predictor',
        description: 'Detect potential escalations early by analyzing sentiment in ticket conversations.',
        industry: 'Technology',
        function: 'Customer Support',
        useCase: 'Customer Success',
        agentType: 'Predictive AI',
        integrations: ['zendesk', 'slack'],
        tags: ['Support', 'Analytics'],
        featured: true
    },
    {
        id: 'supp-3',
        title: 'Support Ticket Insights',
        description: 'Examine a collection of customer support tickets to identify recurring issues and knowledge gaps.',
        industry: 'Technology',
        function: 'Customer Support',
        useCase: 'Analytics',
        agentType: 'Analytics',
        integrations: ['salesforce', 'jira'],
        tags: ['Support', 'IT']
    },

    // Marketing Agents
    {
        id: 'mkt-1',
        title: 'De-Duplication Agent',
        description: 'Identify and manage duplicate company records in HubSpot to maintain data hygiene.',
        industry: 'Marketing',
        function: 'Marketing',
        useCase: 'Data Mgmt',
        agentType: 'Data Utility',
        integrations: ['hubspot'],
        tags: ['Marketing', 'Data'],
        badge: 'Template'
    },
    {
        id: 'mkt-2',
        title: 'Social Media Content Generator',
        description: 'Generate engaging social media captions and image ideas based on blog posts.',
        industry: 'Marketing',
        function: 'Marketing',
        useCase: 'Content Creation',
        agentType: 'Generative AI',
        integrations: ['instagram', 'linkedin', 'twitter'],
        tags: ['Marketing', 'Social']
    },

    // IT & Finance
    {
        id: 'it-1',
        title: 'IT Access Request Handler',
        description: 'Automate approvals and provisioning for software access requests.',
        industry: 'IT',
        function: 'IT',
        useCase: 'Access Management',
        agentType: 'Workflow',
        integrations: ['okta', 'jira', 'slack'],
        tags: ['IT', 'Security']
    },
    {
        id: 'fin-1',
        title: 'Invoice Processing Bot',
        description: 'Extract data from invoices and automatically enter it into the accounting system.',
        industry: 'Finance',
        function: 'Finance',
        useCase: 'AP Automation',
        agentType: 'Document AI',
        integrations: ['quickbooks', 'gmail'],
        tags: ['Finance', 'Automation']
    },
    // Operations Agents
    {
        id: 'ops-1',
        title: 'Inventory Forecaster',
        description: 'Predict inventory needs based on historical sales data and seasonal trends.',
        industry: 'Retail',
        function: 'Operations',
        useCase: 'Supply Chain',
        agentType: 'Predictive AI',
        integrations: ['shopify', 'netsuite'],
        tags: ['Operations', 'Supply Chain']
    },
    // General Agents
    {
        id: 'gen-1',
        title: 'Meeting Assistant Pro',
        description: 'Records, transcribes, and summarizes meetings for any department.',
        industry: 'General',
        function: 'General',
        useCase: 'Productivity',
        agentType: 'Assistant',
        integrations: ['zoom', 'teams', 'meet'],
        tags: ['General', 'Productivity']
    },
    // Cyber Security Agents
    {
        id: 'sec-1',
        title: 'Cyber Security Newsletter Bot',
        description: 'Searches for recent cyber security news (Google, GPT, Linux Foundation) and posts a curated newsletter to LinkedIn.',
        industry: 'IT',
        function: 'IT',
        useCase: 'Content Creation',
        agentType: 'Generative AI',
        integrations: ['linkedin', 'tavily'],
        tags: ['Security', 'LinkedIn', 'News'],
        prompt: 'Search for recent cyber security news and create a LinkedIn post.'
    }
];

export const filters = {
    industries: ['Technology', 'Healthcare', 'Banking', 'Retail', 'Manufacturing', 'Education'],
    functions: ['HR', 'Sales', 'Marketing', 'Customer Support', 'IT', 'Finance', 'Operations'],
    useCases: ['Onboarding', 'Meeting Prep', 'Ticket Management', 'Lead Gen', 'Content Creation'],
    agentTypes: ['Conversational', 'Assistant', 'Process Automation', 'Predictive AI', 'Generative AI'],
    integrations: ['Slack', 'Zendesk', 'HubSpot', 'Salesforce', 'Jira', 'Teams', 'Gmail']
};
