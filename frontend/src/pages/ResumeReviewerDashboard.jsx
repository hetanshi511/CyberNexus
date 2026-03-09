import React, { useState, useEffect } from 'react';
// import { useNavigate } from 'react-router-dom';
import { 
    Briefcase, UploadCloud, Users, CheckCircle, 
    AlertCircle, FileText, Loader2, List, Star, Link as LinkIcon, X, HardDrive
} from 'lucide-react';
import { auth } from '../firebase';
import { signInWithPopup, GoogleAuthProvider } from 'firebase/auth';

const ResumeReviewerDashboard = () => {
    const [jobDescription, setJobDescription] = useState('');
    const [resumeFiles, setResumeFiles] = useState([]);
    const [driveFiles, setDriveFiles] = useState([]); // Store selected drive file objects
    const [driveToken, setDriveToken] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [report, setReport] = useState(null);
    const [error, setError] = useState('');
    const [showPicker, setShowPicker] = useState(false);
    const [activeTab, setActiveTab] = useState('local'); // 'local' or 'drive'
    
    // Load Google scripts for Picker and OAuth
    useEffect(() => {
        const apiScript = document.createElement('script');
        apiScript.src = 'https://apis.google.com/js/api.js';
        apiScript.async = true;
        apiScript.defer = true;
        document.body.appendChild(apiScript);

        // Load picker gapi library immediately after script loads
        apiScript.onload = () => {
            if (window.gapi) {
                window.gapi.load('picker');
            }
        };

        return () => {
            if (document.body.contains(apiScript)) document.body.removeChild(apiScript);
        };
    }, []);
    // const navigate = useNavigate();

    const handleFileChange = (e) => {
        if (e.target.files) {
            setResumeFiles(Array.from(e.target.files));
        }
    };

    const handleAnalyze = async () => {
        if (!jobDescription || jobDescription.trim() === '') {
            setError('Job Description is mandatory. Please provide a job description.');
            return;
        }

        if (resumeFiles.length === 0 && driveFiles.length === 0) {
            setError('Please upload at least one candidate resume or select from Google Drive.');
            return;
        }

        setError('');
        setIsAnalyzing(true);
        setReport(null);

        try {
            const formData = new FormData();
            formData.append('job_description', jobDescription);
            
            if (driveFiles.length > 0 && driveToken) {
                const ids = driveFiles.map(f => f.id);
                formData.append('drive_file_ids', JSON.stringify(ids));
                formData.append('drive_access_token', driveToken);
            }
            
            resumeFiles.forEach((file) => {
                formData.append('resumes', file);
            });

            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/api/execute_resume_reviewer`, {
                method: 'POST',
                // Don't set Content-Type header manually when using FormData, 
                // fetch will automatically set it to multipart/form-data with the correct boundary
                body: formData,
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to analyze resumes.');
            }

            const data = await response.json();
            
            if (data.status === 'Failed') {
                throw new Error(data.report || 'Agent failed to process resumes.');
            }

            setReport(data.report);
        } catch (err) {
            console.error('Resume Analysis Error:', err);
            setError(err.message || 'An error occurred during analysis.');
        } finally {
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#f8fbff] p-6 lg:p-10 font-sans mt-16 pb-20">
            <div className="max-w-7xl mx-auto mb-10">
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
                    <Users className="w-10 h-10 text-blue-600" />
                    AI Resume Reviewer
                </h1>
                <p className="text-gray-500 mt-2 font-medium max-w-3xl">
                    Automate your candidate screening process. Upload resumes and provide a job description to instantly score and shortlist candidates based entirely on objective data.
                </p>
            </div>

            {/* Input Section */}
            <div className="max-w-7xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8 mb-10">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Job Description */}
                    <div>
                        <label className="block text-sm font-bold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                            <Briefcase className="w-4 h-4 text-blue-500" />
                            Job Description <span className="text-red-500">*</span>
                        </label>
                        <textarea 
                            value={jobDescription}
                            onChange={(e) => setJobDescription(e.target.value)}
                            placeholder="Enter the required skills, experience levels, and preferred qualifications..."
                            className="w-full h-48 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all resize-none text-gray-700"
                        />
                    </div>

                    {/* Resume Uploads */}
                    <div>
                        <label className="block text-sm font-bold text-gray-700 uppercase tracking-wide mb-3 flex items-center gap-2">
                            <Users className="w-4 h-4 text-blue-500" />
                            Candidate Resumes <span className="text-red-500">*</span>
                        </label>
                        
                        <div 
                            onClick={() => setShowPicker(true)}
                            className="border-2 border-dashed border-blue-300 rounded-xl h-48 flex flex-col items-center justify-center p-6 bg-blue-50 hover:bg-blue-100 transition-colors cursor-pointer group relative"
                        >
                            <div className="flex gap-4 mb-3">
                                <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform">
                                    <UploadCloud className="w-6 h-6" />
                                </div>
                                <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-emerald-600 group-hover:scale-110 transition-transform">
                                    <HardDrive className="w-6 h-6" />
                                </div>
                            </div>
                            <p className="text-base font-bold text-blue-900">Add Candidates</p>
                            <p className="text-sm text-blue-600/80 mt-1">Browse files or import from Google Drive</p>

                            {(resumeFiles.length > 0 || driveFiles.length > 0) && (
                                <div className="mt-4 flex flex-wrap gap-2 justify-center">
                                    {resumeFiles.length > 0 && (
                                        <span className="px-3 py-1 bg-white shadow-sm border border-blue-100 text-blue-700 text-xs font-bold rounded-md flex items-center gap-1">
                                            <FileText className="w-3 h-3" /> {resumeFiles.length} Local File(s)
                                        </span>
                                    )}
                                    {driveFiles.length > 0 && (
                                        <span className="px-3 py-1 bg-white shadow-sm border border-emerald-100 text-emerald-700 text-xs font-bold rounded-md flex items-center gap-1">
                                            <HardDrive className="w-3 h-3" /> {driveFiles.length} Drive File(s)
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {error && (
                    <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-sm flex items-center gap-2">
                        <AlertCircle className="w-5 h-5" /> {error}
                    </div>
                )}

                <div className="mt-8 flex justify-end">
                    <button 
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                        className="px-8 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 transition-all shadow-md shadow-blue-200 flex items-center gap-2 disabled:opacity-70"
                    >
                        {isAnalyzing ? (
                            <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing Candidates...</>
                        ) : (
                            <><Users className="w-5 h-5" /> Score Resumes</>
                        )}
                    </button>
                </div>
            </div>

            {/* Results Section */}
            {report && (
                <div className="max-w-7xl mx-auto space-y-10">
                    
                    {/* Metrics */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-4">
                            <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center">
                                <List className="w-7 h-7 text-blue-600" />
                            </div>
                            <div>
                                <p className="text-sm font-bold text-gray-500 uppercase tracking-wide">Total Evaluated</p>
                                <h3 className="text-4xl font-black text-gray-900">{report.total_evaluated}</h3>
                            </div>
                        </div>
                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-emerald-100 flex items-center gap-4">
                            <div className="w-14 h-14 rounded-full bg-emerald-50 flex items-center justify-center">
                                <Star className="w-7 h-7 text-emerald-600" />
                            </div>
                            <div>
                                <p className="text-sm font-bold text-gray-500 uppercase tracking-wide">Shortlisted (Score ≥ 8)</p>
                                <h3 className="text-4xl font-black text-emerald-600">{report.total_shortlisted}</h3>
                            </div>
                        </div>
                    </div>

                    {/* Shortlisted Candidates */}
                    {report.shortlisted_candidates && report.shortlisted_candidates.length > 0 && (
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                                <Star className="w-6 h-6 text-emerald-500" />
                                Shortlisted Candidates
                            </h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {report.shortlisted_candidates.map((cand, idx) => (
                                    <div key={idx} className="bg-white rounded-2xl shadow-md border-2 border-emerald-100 p-6 relative overflow-hidden flex flex-col">
                                        <div className="absolute top-0 right-0 bg-emerald-500 text-white font-black text-lg px-4 py-2 rounded-bl-2xl">
                                            {cand.score}/10
                                        </div>
                                        <h3 className="text-xl font-bold text-gray-900 pr-12 truncate">{cand.name}</h3>
                                        <a href={`mailto:${cand.email}`} className="text-sm text-blue-600 hover:underline mb-4 inline-block truncate">
                                            {cand.email}
                                        </a>
                                        <div className="flex-1">
                                            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Evaluation Summary</p>
                                            <p className="text-sm text-gray-700 leading-relaxed italic border-l-2 border-emerald-200 pl-3">
                                                {cand.summary}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* All Candidates */}
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                            <List className="w-6 h-6 text-gray-500" />
                            All Candidates Breakdown
                        </h2>
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/5">Candidate Name</th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/5">Email Address</th>
                                            <th className="px-6 py-4 text-center text-xs font-bold text-gray-500 uppercase tracking-wider w-24">Score</th>
                                            <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Evaluation Summary</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-100">
                                        {report.all_candidates.map((cand, idx) => (
                                            <tr key={idx} className={`hover:bg-gray-50 transition-colors ${cand.score >= 8 ? 'bg-emerald-50/30' : ''}`}>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">
                                                    {cand.name}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 hover:underline cursor-pointer">
                                                    <a href={`mailto:${cand.email}`}>{cand.email}</a>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-center">
                                                    <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full font-black text-sm ${
                                                        cand.score >= 8 ? 'bg-emerald-100 text-emerald-800 ring-2 ring-emerald-400' :
                                                        cand.score >= 5 ? 'bg-yellow-100 text-yellow-800' :
                                                        'bg-red-100 text-red-800'
                                                    }`}>
                                                        {cand.score}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-sm text-gray-600 leading-relaxed italic max-w-lg">
                                                    {cand.summary}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                </div>
            )}

            {/* Unified File Picker Modal */}
            {showPicker && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
                    <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        {/* Modal Header */}
                        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                <UploadCloud className="w-5 h-5 text-blue-600" />
                                Select Candidate Resumes
                            </h3>
                            <button 
                                onClick={() => setShowPicker(false)}
                                className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-full transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Tabs */}
                        <div className="flex border-b border-gray-100">
                            <button
                                onClick={() => setActiveTab('local')}
                                className={`flex-1 py-4 text-sm font-bold flex items-center justify-center gap-2 ${
                                    activeTab === 'local' 
                                        ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/30' 
                                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                                }`}
                            >
                                <FileText className="w-4 h-4" /> Browse Local
                            </button>
                            <button
                                onClick={() => setActiveTab('drive')}
                                className={`flex-1 py-4 text-sm font-bold flex items-center justify-center gap-2 ${
                                    activeTab === 'drive' 
                                        ? 'text-emerald-600 border-b-2 border-emerald-600 bg-emerald-50/30' 
                                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                                }`}
                            >
                                <HardDrive className="w-4 h-4" /> Google Drive
                            </button>
                        </div>

                        {/* Tab Content */}
                        <div className="p-6">
                            {activeTab === 'local' && (
                                <div className="animate-in fade-in duration-300">
                                    <div className="border-2 border-dashed border-gray-300 rounded-xl h-64 flex flex-col items-center justify-center p-8 bg-gray-50 hover:bg-gray-100 transition-colors relative">
                                        <input 
                                            type="file" 
                                            multiple 
                                            accept=".pdf only"
                                            onChange={handleFileChange}
                                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                        />
                                        <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4">
                                            <UploadCloud className="w-8 h-8" />
                                        </div>
                                        <p className="text-lg font-bold text-gray-800">Drag & Drop Resumes</p>
                                        <p className="text-sm text-gray-500 mt-2 text-center max-w-sm">
                                            Click anywhere in this box to browse your computer. Supports PDF files.
                                        </p>
                                        
                                        {resumeFiles.length > 0 && (
                                            <div className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white text-sm font-bold rounded-lg shadow-sm">
                                                {resumeFiles.length} file(s) selected automatically
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {activeTab === 'drive' && (
                                <div className="animate-in fade-in duration-300">
                                    <div className="bg-emerald-50/50 rounded-xl p-6 border border-emerald-100 text-center relative overflow-hidden">
                                        
                                        <div className="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
                                            <HardDrive className="w-10 h-10" />
                                        </div>
                                        
                                        <h4 className="text-xl font-bold text-gray-900 mb-2">Connect Google Drive</h4>
                                        <p className="text-sm text-gray-600 max-w-sm mx-auto mb-8">
                                            Select and import candidate resumes directly from your Google Drive without downloading them first.
                                        </p>
                                        
                                        <button 
                                            onClick={async () => {
                                                if (!window.google || !window.gapi) {
                                                    alert("Google Picker API is still loading. Please try again in a few seconds.");
                                                    return;
                                                }

                                                try {
                                                    // Use Firebase Auth to get the Drive OAuth token instead of setting up a separate GIS Client ID
                                                    const provider = new GoogleAuthProvider();
                                                    provider.addScope('https://www.googleapis.com/auth/drive.readonly');
                                                    
                                                    const result = await signInWithPopup(auth, provider);
                                                    const credential = GoogleAuthProvider.credentialFromResult(result);
                                                    const token = credential?.accessToken;

                                                    if (token) {
                                                        setDriveToken(token);
                                                        
                                                        const view = new window.google.picker.DocsView(window.google.picker.ViewId.DOCS)
                                                            .setIncludeFolders(true)
                                                            .setSelectFolderEnabled(false);
                                                        
                                                        const picker = new window.google.picker.PickerBuilder()
                                                            .addView(view)
                                                            .setOAuthToken(token)
                                                            .setDeveloperKey(import.meta.env.VITE_GOOGLE_PICKER_API_KEY || import.meta.env.VITE_FIREBASE_API_KEY) 
                                                            .setCallback((data) => {
                                                                if (data.action === window.google.picker.Action.PICKED) {
                                                                    const files = data.docs;
                                                                    setDriveFiles(prev => [...prev, ...files.map(f => ({ id: f.id, name: f.name }))]);
                                                                }
                                                            })
                                                            .build();
                                                        picker.setVisible(true);
                                                    } else {
                                                        throw new Error("Could not retrieve Google Drive access token from Firebase auth result.");
                                                    }
                                                } catch (err) {
                                                    console.error("Google Picker Initialization/Auth Error:", err);
                                                    alert(err.message || "Failed to authenticate with Google Drive.");
                                                }
                                            }}
                                            className="px-8 py-3 bg-white border-2 border-emerald-500 text-emerald-700 font-bold rounded-xl shadow-sm hover:bg-emerald-50 transition-colors inline-flex items-center gap-2 relative z-10"
                                        >
                                            <HardDrive className="w-5 h-5" /> Open Google Picker
                                        </button>

                                        {driveFiles.length > 0 && (
                                            <div className="mt-8 text-left bg-white p-4 rounded-xl shadow-sm border border-emerald-100 animate-in slide-in-from-bottom-2">
                                                <h5 className="text-sm font-bold text-gray-700 border-b border-gray-100 pb-2 mb-3">Selected Drive Files ({driveFiles.length})</h5>
                                                <ul className="space-y-2 max-h-32 overflow-y-auto pr-2 custom-scrollbar">
                                                    {driveFiles.map((file, idx) => (
                                                        <li key={idx} className="flex flex-col text-sm bg-gray-50 p-2 rounded-lg relative group">
                                                            <span className="font-medium text-gray-800 truncate pr-6">{file.name}</span>
                                                            <button 
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setDriveFiles(prev => prev.filter((_, i) => i !== idx));
                                                                }}
                                                                className="absolute right-2 top-2 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                            >
                                                                <X className="w-4 h-4" />
                                                            </button>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Modal Footer */}
                        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                            <button 
                                onClick={() => setShowPicker(false)}
                                className="px-5 py-2.5 text-gray-600 font-semibold hover:bg-gray-200 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button 
                                onClick={() => setShowPicker(false)}
                                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-sm transition-colors"
                            >
                                Done
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ResumeReviewerDashboard;
