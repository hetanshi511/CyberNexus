import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { User, LogOut } from 'lucide-react';
import { useState } from 'react';

const Navbar = () => {
    const { currentUser, logout } = useAuth();
    const navigate = useNavigate();
    const [showDropdown, setShowDropdown] = useState(false);

    const handleLogout = async () => {
        try {
            await logout();
            navigate('/login');
        } catch (error) {
            console.error("Failed to log out", error);
        }
    };

    return (
        <nav className="sticky top-0 z-50 bg-[#d7e4f5]/90 backdrop-blur-sm px-6 py-4">
            <div className="container mx-auto max-w-7xl flex items-center justify-between">
                <Link to="/" className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full border-[3px] border-blue-600"></div>
                    <span className="text-lg font-bold text-gray-900 tracking-tight">Infopercept Marketplace</span>
                </Link>

                {currentUser ? (
                    <div className="relative">
                        <button
                            onClick={() => setShowDropdown(!showDropdown)}
                            className="flex items-center gap-3 hover:bg-white/50 py-1 px-2 rounded-full transition-colors"
                        >
                            <span className="text-sm font-medium text-gray-700 hidden sm:block">
                                {currentUser.email}
                            </span>
                            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center border border-blue-200 text-blue-700 overflow-hidden">
                                {currentUser.photoURL ? (
                                    <img src={currentUser.photoURL} alt="Profile" className="w-full h-full object-cover" />
                                ) : (
                                    <User className="w-4 h-4" />
                                )}
                            </div>
                        </button>

                        {showDropdown && (
                            <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-1 overflow-hidden animate-in fade-in zoom-in duration-200">
                                <div className="px-4 py-2 border-b border-gray-50">
                                    <p className="text-xs text-gray-500">Signed in as</p>
                                    <p className="text-sm font-medium text-gray-900 truncate">{currentUser.email}</p>
                                </div>
                                <button
                                    onClick={handleLogout}
                                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors"
                                >
                                    <LogOut className="w-4 h-4" />
                                    Sign out
                                </button>
                            </div>
                        )}
                    </div>
                ) : (
                    <button
                        onClick={() => navigate('/login')}
                        className="px-6 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm cursor-pointer"
                    >
                        Login
                    </button>
                )}
            </div>
        </nav>
    );
};

export default Navbar;
