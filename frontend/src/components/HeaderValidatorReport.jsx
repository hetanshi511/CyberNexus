import React from 'react';
import { Shield, ShieldAlert, AlertTriangle, Info, CheckCircle, Server, Globe, Clock, Hash } from 'lucide-react';

const HeaderValidatorReport = ({ report }) => {
    if (!report) return null;

    const {
        site,
        ip_address,
        report_time,
        status_code,
        security_score,
        grade,
        present_security_headers,
        missing_headers,
        raw_headers,
        upcoming_headers,
        security_issues = [],
        llm_analysis = ''
    } = report;

    // Helper for rendering the score grade
    const getScoreColor = (score) => {
        if (['A', 'A+', 'A-'].includes(score)) return 'bg-green-100 text-green-700 border-green-200';
        if (['B', 'B+', 'B-'].includes(score)) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
        if (['C', 'C+', 'C-'].includes(score)) return 'bg-orange-100 text-orange-700 border-orange-200';
        return 'bg-red-100 text-red-700 border-red-200';
    };

    return (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden font-sans">
            {/* Header Section */}
            <div className="bg-gray-50 border-b border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-3 bg-blue-100 text-blue-700 rounded-xl">
                        <Shield className="w-6 h-6" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900">Security Report Summary</h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-4 bg-white rounded-xl border border-gray-100 shadow-sm">
                    {/* Grade Block */}
                    <div className="flex flex-col items-center justify-center p-4 border-r border-gray-100 last:border-0 relative">
                         <div className={`w-20 h-20 rounded-full flex items-center justify-center border-4 shadow-inner text-4xl font-extrabold ${getScoreColor(grade || security_score)}`}>
                            {grade || security_score}
                        </div>
                        <span className="text-sm font-semibold text-gray-500 mt-2 uppercase tracking-wide">
                            Score: {security_score !== undefined && !isNaN(security_score) ? `${security_score} / 100` : ''}
                        </span>
                    </div>

                    {/* Site Details */}
                    <div className="col-span-1 md:col-span-1 lg:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                        <div className="flex items-start gap-3">
                            <Globe className="w-5 h-5 text-gray-400 mt-0.5" />
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-bold tracking-wider">Site</p>
                                <a href={site} target="_blank" rel="noreferrer" className="text-blue-600 font-medium hover:underline break-all">
                                    {site}
                                </a>
                            </div>
                        </div>
                        <div className="flex items-start gap-3">
                            <Server className="w-5 h-5 text-gray-400 mt-0.5" />
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-bold tracking-wider">IP Address</p>
                                <p className="text-gray-800 font-medium">{ip_address}</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-3">
                            <Clock className="w-5 h-5 text-gray-400 mt-0.5" />
                            <div>
                                <p className="text-xs text-gray-500 uppercase font-bold tracking-wider">Report Time</p>
                                <p className="text-gray-800 font-medium">{report_time}</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-3 flex-col sm:col-span-2 mt-2 border-t border-gray-100 pt-3">
                            <div className="flex items-center justify-between w-full">
                                <p className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">Headers Status Overview</p>
                                <div className="flex gap-3 text-xs font-semibold text-gray-500">
                                    <span className="flex items-center gap-1"><Check className="w-3 h-3 text-green-600"/> Present</span>
                                    <span className="flex items-center gap-1"><X className="w-3 h-3 text-red-600"/> Missing</span>
                                    <span className="flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-orange-600"/> Misconfigured</span>
                                </div>
                            </div>
                             <div className="flex flex-wrap gap-2 mt-1">
                                {/* All core security headers represented as pills */}
                                {['Strict-Transport-Security', 'Content-Security-Policy', 'X-Frame-Options', 'X-Content-Type-Options', 'Referrer-Policy', 'Permissions-Policy', 'X-XSS-Protection', 'Expect-CT', 'Clear-Site-Data'].map(headerName => {
                                    const isMissing = (missing_headers || []).some(h => h.name.toLowerCase() === headerName.toLowerCase());
                                    const isMisconfigured = (security_issues || []).some(cat => cat.category.toLowerCase().includes(headerName.toLowerCase().replace(/-/g, ' ')));
                                    
                                    let statusColor, Icon;
                                    if (isMissing) {
                                        statusColor = 'bg-red-50 text-red-600 border border-red-100';
                                        Icon = X;
                                    } else if (isMisconfigured) {
                                        statusColor = 'bg-orange-50 text-orange-600 border border-orange-100';
                                        Icon = AlertTriangle;
                                    } else {
                                        statusColor = 'bg-green-50 text-green-700 border border-green-100';
                                        Icon = Check;
                                    }

                                    return (
                                        <span key={headerName} className={`px-2.5 py-1 text-xs font-semibold rounded-md flex items-center gap-1 ${statusColor}`}>
                                            <Icon className="w-3 h-3"/>
                                            {headerName}
                                        </span>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </div>

                {(missing_headers && missing_headers.length > 0) && (
                     <div className="mt-6 bg-red-50/80 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                         <AlertTriangle className="w-6 h-6 text-red-600 shrink-0 mt-0.5" />
                         <div>
                             <h4 className="text-red-800 font-bold text-sm uppercase tracking-wide">Header Security Warning</h4>
                             <p className="text-red-700 mt-1 text-sm">You are missing {missing_headers.length} recommended core security headers.</p>
                         </div>
                     </div>
                )}
            </div>

            <div className="p-6 space-y-8">
                
                {/* 🤖 AI Agent Analysis Section */}
                {llm_analysis && (
                    <section>
                        <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2 border-b border-gray-100 pb-2">
                            <Shield className="w-5 h-5 text-indigo-500" />
                            AI Security Auditor Remarks
                        </h3>
                        <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-6 text-gray-800 text-sm leading-relaxed prose prose-indigo max-w-none">
                            {/* Simple markdown parsing for the LLM output */}
                            {llm_analysis.split('\n').map((line, i) => {
                                if (line.startsWith('### ')) return <h4 key={i} className="text-lg font-bold mt-4 mb-2">{line.replace('###', '')}</h4>;
                                if (line.startsWith('## ')) return <h3 key={i} className="text-xl font-bold mt-5 mb-3">{line.replace('##', '')}</h3>;
                                if (line.startsWith('# ')) return <h2 key={i} className="text-2xl font-bold mt-6 mb-4">{line.replace('#', '')}</h2>;
                                if (line.startsWith('- ')) return <li key={i} className="ml-4 mb-1">{line.replace('- ', '')}</li>;
                                if (line.trim() === '') return <br key={i} />;
                                // Bold parsing **text**
                                const boldParsed = line.split(/(\*\*.*?\*\*)/g).map((part, j) => {
                                    if (part.startsWith('**') && part.endsWith('**')) {
                                        return <strong key={j}>{part.slice(2, -2)}</strong>;
                                    }
                                    return part;
                                });
                                return <p key={i} className="mb-2">{boldParsed}</p>;
                            })}
                        </div>
                    </section>
                )}

                {/* 🛑 Misconfigured Parameters */}
                {security_issues && security_issues.length > 0 && (
                    <section>
                        <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2 border-b border-gray-100 pb-2">
                            <AlertTriangle className="w-5 h-5 text-orange-500" />
                            Configuration Weaknesses
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {security_issues.map((cat, idx) => (
                                <div key={idx} className="bg-orange-50 border border-orange-100 rounded-lg p-5 shadow-sm">
                                    <h4 className="font-bold text-orange-900 mb-3 text-sm uppercase tracking-wide">{cat.category}</h4>
                                    <ul className="space-y-2">
                                        {cat.issues.map((issue, j) => (
                                            <li key={j} className="flex flex-row items-start gap-2 text-sm text-orange-800">
                                                <X className="w-4 h-4 mt-0.5 shrink-0 text-orange-600"/>
                                                {issue}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Missing Headers Section */}
                {missing_headers && missing_headers.length > 0 && (
                    <section>
                        <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2 border-b border-gray-100 pb-2">
                            <ShieldAlert className="w-5 h-5 text-red-500" />
                            Missing Headers
                        </h3>
                        <div className="space-y-6">
                            {['Critical', 'Recommended', 'Optional'].map(category => {
                                const categoryHeaders = missing_headers.filter(h => h.category === category || (!h.category && category === 'Critical'));
                                if (categoryHeaders.length === 0) return null;
                                
                                let catColor = "text-red-800 bg-red-100 border-red-200";
                                let pillColor = "bg-red-100 text-red-800";
                                if (category === 'Recommended') {
                                    catColor = "text-orange-800 bg-orange-100 border-orange-200";
                                    pillColor = "bg-orange-100 text-orange-800";
                                } else if (category === 'Optional') {
                                    catColor = "text-blue-800 bg-blue-100 border-blue-200";
                                    pillColor = "bg-blue-100 text-blue-800";
                                }

                                return (
                                    <div key={category} className={`border border-gray-200 rounded-xl p-5 ${category === 'Critical' ? 'bg-red-50/30' : (category === 'Recommended' ? 'bg-orange-50/30' : 'bg-blue-50/30')}`}>
                                        <h4 className={`font-bold mb-4 text-sm uppercase tracking-wider ${catColor.split(' ')[0]}`}>{category} Missing Headers</h4>
                                        <div className="space-y-3">
                                            {categoryHeaders.map((header, idx) => (
                                                <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm flex flex-col sm:flex-row sm:items-start gap-4">
                                                    <div className="sm:w-1/3 shrink-0">
                                                         <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-sm font-bold rounded-md whitespace-nowrap overflow-hidden text-ellipsis w-full ${pillColor}`}>
                                                            {category === 'Optional' ? <Info className="w-4 h-4 shrink-0" /> : (category === 'Recommended' ? <AlertTriangle className="w-4 h-4 shrink-0" /> : <X className="w-4 h-4 shrink-0" />)}
                                                            {header.name}
                                                         </span>
                                                    </div>
                                                    <div className="sm:w-2/3">
                                                        <p className="text-gray-600 text-sm leading-relaxed">{header.description}</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </section>
                )}

                {/* Raw Headers Section */}
                {raw_headers && raw_headers.length > 0 && (
                    <section>
                        <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2 border-b border-gray-100 pb-2">
                            <Hash className="w-5 h-5 text-gray-500" />
                            Raw Headers
                        </h3>
                        <div className="bg-gray-900 rounded-xl overflow-hidden shadow-inner">
                            <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                                <table className="min-w-full text-left text-sm whitespace-nowrap font-mono">
                                    <thead className="bg-gray-800 sticky top-0">
                                        <tr>
                                            <th scope="col" className="px-6 py-3 text-gray-400 font-semibold border-b border-gray-700">Header Name</th>
                                            <th scope="col" className="px-6 py-3 text-gray-400 font-semibold border-b border-gray-700">Value</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-800">
                                        {raw_headers.map((header, idx) => (
                                            <tr key={idx} className="hover:bg-gray-800/50 transition-colors">
                                                <td className="px-6 py-3 font-semibold text-blue-300 align-top">{header.name}</td>
                                                <td className="px-6 py-3 text-gray-300 break-all whitespace-normal">
                                                    {(header.name.toLowerCase() === 'set-cookie' && header.value.includes(', ')) ? (
                                                        <div className="space-y-1">
                                                            {header.value.split(', ').map((cookieStr, i) => (
                                                                <div key={i} className="pl-4 border-l-2 border-gray-700 bg-gray-800/30 p-1.5 rounded text-xs hover:bg-gray-800/60 transition-colors cursor-text">
                                                                    {cookieStr}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        header.value
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>
                )}

                {/* Upcoming Headers Section */}
                {upcoming_headers && upcoming_headers.length > 0 && (
                    <section>
                        <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2 border-b border-gray-100 pb-2">
                            <Info className="w-5 h-5 text-blue-500" />
                            Upcoming Headers
                        </h3>
                        <div className="space-y-4">
                            {upcoming_headers.map((header, idx) => (
                                <div key={idx} className={`bg-white border rounded-lg p-5 shadow-sm transition-shadow ${header.present ? 'border-green-100' : 'border-gray-200'}`}>
                                    <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                                         <div className="sm:w-1/3 shrink-0">
                                            <span className={`inline-flex items-center gap-1.5 px-3 py-1 text-sm font-bold rounded-md ${header.present ? 'bg-green-100 text-green-800' : 'bg-red-50 text-red-700'}`}>
                                            {header.present ? (
                                                 <><Check className="w-4 h-4 shrink-0" /> {header.name} <span className="text-xs uppercase ml-1 opacity-70">Present</span></>
                                            ) : (
                                                 <><X className="w-4 h-4 shrink-0" /> {header.name} <span className="text-xs uppercase ml-1 opacity-70">Missing</span></>
                                            )}
                                        </span>
                                        </div>
                                        <div className="sm:w-2/3 space-y-2">
                                            <p className="text-gray-600 text-sm leading-relaxed">{header.description}</p>
                                            {header.present && (
                                                <div className="bg-gray-50 p-2 rounded border border-gray-100 font-mono text-xs text-gray-700 mt-2 break-all">
                                                    <strong>Value:</strong> {header.value}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

            </div>
        </div>
    );
};

// Mini icons missing from standard import
const X = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
);
const Check = ({ className }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
);

export default HeaderValidatorReport;
