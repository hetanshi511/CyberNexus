
export const agents = [
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
    },
    {
        id: 'sec-2',
        title: 'Policy Conflict Checker Agent',
        description: 'Analyzes two policy documents (e.g. Internal vs ISO 27001) to identify conflicts, gaps, and compliance issues.',
        industry: 'Legal',
        function: 'Legal',
        useCase: 'Compliance',
        agentType: 'Analysis',
        integrations: ['azure', 'box'],
        tags: ['Compliance', 'Legal', 'Policy'],
        prompt: 'Check for conflicts between the supplied policy documents.'
    },
    {
        id: 'sec-3',
        title: 'Vendor Risk Assessment Agent',
        description: 'Analyzes vendor security documentation/descriptions to assign a risk score and highlight red flags.',
        industry: 'Procurement',
        function: 'Risk',
        useCase: 'Vendor Management',
        agentType: 'Risk Analysis',
        integrations: ['onedrive', 'googledrive'],
        tags: ['Risk', 'Vendor', 'Security'],
        prompt: 'Analyze the vendor security posture and calculate a risk score.'
    }
];

export const filters = {
    industries: ['Technology', 'Healthcare', 'Banking', 'Retail', 'Manufacturing', 'Education'],
    functions: ['HR', 'Sales', 'Marketing', 'Customer Support', 'IT', 'Finance', 'Operations'],
    useCases: ['Onboarding', 'Meeting Prep', 'Ticket Management', 'Lead Gen', 'Content Creation'],
    agentTypes: ['Conversational', 'Assistant', 'Process Automation', 'Predictive AI', 'Generative AI'],
    integrations: ['Slack', 'Zendesk', 'HubSpot', 'Salesforce', 'Jira', 'Teams', 'Gmail']
};
