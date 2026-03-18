
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
    },
    {
        id: 'compliance-bot',
        title: 'Compliance Verification Agent',
        description: 'Fetches recent Jira tickets from a Project and analyzes them for compliance alignment in a tabular report.',
        industry: 'Compliance',
        function: 'Audit',
        useCase: 'Alignment Check',
        agentType: 'Analysis',
        integrations: ['jira'],
        tags: ['Compliance', 'Jira', 'Audit'],
        prompt: 'Analyze tickets in this Jira Project for compliance.'
    },
    {
        id: 'content-reviewer',
        title: 'Content Reviewer Agent',
        description: 'Crawls a given website to identify typos, spelling, grammatical, and punctuation errors, generating a structured report.',
        industry: 'Marketing',
        function: 'Marketing',
        useCase: 'Content Creation',
        agentType: 'Analysis',
        integrations: ['openai', 'web'],
        tags: ['SEO', 'Marketing', 'Content'],
        prompt: 'Review the content on this website for any grammar or spelling mistakes.'
    },
    {
        id: 'header-validator',
        title: 'Header Validator Agent',
        description: 'Performs a deep security analysis of site headers, checking for missing or vulnerable configurations.',
        industry: 'Security',
        function: 'IT',
        useCase: 'Security Check',
        agentType: 'Analysis',
        integrations: ['web'],
        tags: ['Security', 'Headers', 'Audit'],
        prompt: 'Analyze the HTTP headers of the provided site for security risks.'
    },
    {
        id: 'resume-reviewer',
        title: 'Resume Reviewer Agent',
        description: 'Evaluates candidate resumes against a given job description and assigns scores based on alignment.',
        industry: 'HR',
        function: 'HR',
        useCase: 'Screening',
        agentType: 'Analysis',
        integrations: ['googledrive', 'local'],
        tags: ['HR', 'Resume', 'Screening', 'Hiring'],
        prompt: 'Review candidate resumes against the job description.'
    },
    {
        id: 'scheduler-agent',
        title: 'Interview Scheduler Agent',
        description: "Automatically schedules candidate interviews by finding the best available slot on the recruiter's Google Calendar, generating a meeting link, and sending a confirmation email.",
        industry: 'HR',
        function: 'HR',
        useCase: 'Onboarding',
        agentType: 'Process Automation',
        integrations: ['googlecalendar', 'email'],
        tags: ['HR', 'Scheduling', 'Calendar', 'Hiring'],
        prompt: 'Schedule an interview for a candidate with a recruiter.'
    },
    {
        id: 'email-security',
        title: 'Email Security Agent',
        description: 'Real-time Gmail inbox monitoring that detects phishing, SPAM, and FRAUD using VirusTotal scanning and LLM analysis — then auto-labels and quarantines threats.',
        industry: 'Security',
        function: 'IT',
        useCase: 'Threat Detection',
        agentType: 'Process Automation',
        integrations: ['gmail', 'virustotal'],
        tags: ['Security', 'Email', 'Phishing', 'Fraud'],
        prompt: 'Scan my inbox for phishing, spam, and fraud emails.'
    }
];

export const filters = {
    industries: ['Technology', 'Healthcare', 'Banking', 'Retail', 'Manufacturing', 'Education', 'Compliance'],
    functions: ['HR', 'Sales', 'Marketing', 'Customer Support', 'IT', 'Finance', 'Operations', 'Audit', 'Risk', 'Legal'],
    useCases: ['Onboarding', 'Meeting Prep', 'Ticket Management', 'Lead Gen', 'Content Creation', 'Alignment Check', 'Vendor Management', 'Threat Detection', 'Security Check'],
    agentTypes: ['Conversational', 'Assistant', 'Process Automation', 'Predictive AI', 'Generative AI', 'Analysis', 'Risk Analysis'],
    integrations: ['Slack', 'Zendesk', 'HubSpot', 'Salesforce', 'Jira', 'Teams', 'Gmail', 'Azure', 'Box', 'OneDrive', 'GoogleDrive', 'VirusTotal']
};
