// src/components/Sidebar.jsx - INTEGRATED WITH BACKEND

import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import { 
    MessageSquare, 
    Search, 
    LayoutDashboard, 
    Settings, 
    ChevronLeft, 
    ChevronRight,
    Plus,
    Trash2,
    MoreVertical
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import PropTypes from 'prop-types';
import { api } from '../lib/api';

// ============================================================================
// NAV ITEM COMPONENT
// ============================================================================

const NavItem = ({ icon, text, isExpanded, active, onClick, to }) => {
    const content = (
        <li 
            className={`
                relative flex items-center py-2 px-3 my-1
                font-medium rounded-md cursor-pointer
                transition-colors group
                ${active 
                    ? "bg-gradient-to-tr from-indigo-200 to-indigo-100 text-indigo-800" 
                    : "hover:bg-indigo-50 text-gray-600"
                }
            `}
            onClick={onClick}
        >
            {icon}
            <span className={`
                overflow-hidden transition-all 
                ${isExpanded ? "w-40 ml-3" : "w-0"}
            `}>
                {text}
            </span>

            {/* Tooltip */}
            {!isExpanded && (
                <div className={`
                    absolute left-full rounded-md px-2 py-1 ml-6
                    bg-indigo-100 text-indigo-800 text-sm
                    invisible opacity-20 -translate-x-3 transition-all
                    group-hover:visible group-hover:opacity-100 group-hover:translate-x-0
                    whitespace-nowrap z-50
                `}>
                    {text}
                </div>
            )}
        </li>
    );

    return to ? <Link to={to}>{content}</Link> : content;
};

NavItem.propTypes = {
    icon: PropTypes.node.isRequired,
    text: PropTypes.string.isRequired,
    isExpanded: PropTypes.bool.isRequired,
    active: PropTypes.bool,
    onClick: PropTypes.func,
    to: PropTypes.string,
};

// ============================================================================
// CHAT ITEM COMPONENT
// ============================================================================

const ChatItem = ({ chat, isExpanded, isActive, onDelete }) => {
    const [showMenu, setShowMenu] = useState(false);

    const handleDelete = (e) => {
        e.stopPropagation();
        if (window.confirm(`Delete "${chat.title}"?`)) {
            onDelete(chat.conversation_id);
        }
        setShowMenu(false);
    };

    return (
        <Link to={`/dashboard/chats/${chat.conversation_id}`}>
            <li className={`
                relative flex items-center justify-between py-2 px-3 my-1
                rounded-md cursor-pointer transition-colors group
                ${isActive 
                    ? "bg-indigo-100 text-indigo-800" 
                    : "hover:bg-gray-50 text-gray-700"
                }
            `}>
                <div className="flex items-center overflow-hidden flex-1">
                    <MessageSquare size={16} className="flex-shrink-0" />
                    <span className={`
                        overflow-hidden text-ellipsis whitespace-nowrap transition-all
                        ${isExpanded ? "w-full ml-3" : "w-0"}
                    `}>
                        {chat.title}
                    </span>
                </div>

                {/* Menu Button */}
                {isExpanded && (
                    <div className="relative">
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                setShowMenu(!showMenu);
                            }}
                            className="p-1 rounded hover:bg-gray-200 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                            <MoreVertical size={14} />
                        </button>

                        {/* Dropdown Menu */}
                        {showMenu && (
                            <div className="absolute right-0 top-full mt-1 bg-white rounded-md shadow-lg border z-50 min-w-[120px]">
                                <button
                                    onClick={handleDelete}
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                                >
                                    <Trash2 size={14} />
                                    Delete
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* Tooltip for collapsed state */}
                {!isExpanded && (
                    <div className={`
                        absolute left-full rounded-md px-2 py-1 ml-6
                        bg-indigo-100 text-indigo-800 text-sm
                        invisible opacity-20 -translate-x-3 transition-all
                        group-hover:visible group-hover:opacity-100 group-hover:translate-x-0
                        whitespace-nowrap z-50 max-w-[200px]
                    `}>
                        {chat.title}
                    </div>
                )}
            </li>
        </Link>
    );
};

ChatItem.propTypes = {
    chat: PropTypes.object.isRequired,
    isExpanded: PropTypes.bool.isRequired,
    isActive: PropTypes.bool,
    onDelete: PropTypes.func.isRequired,
};

// ============================================================================
// MAIN SIDEBAR COMPONENT
// ============================================================================

export default function Sidebar({ isExpanded, onToggle, recentChats, onDeleteChat }) {
    const [search, setSearch] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const location = useLocation();
    const navigate = useNavigate();
    const { user } = useUser();

    // Get active chat ID from URL
    const activeChatId = location.pathname.split('/').pop();

    // Filter chats based on search
    const filteredChats = recentChats.filter(chat =>
        chat.title.toLowerCase().includes(search.toLowerCase())
    );

    // ========================================================================
    // BACKEND INTEGRATION - Delete Chat
    // ========================================================================

    const handleDeleteChat = async (chatId) => {
        try {
            await api.chat.deleteConversation(chatId);
            toast.success('Chat deleted');
            
            // Call parent callback
            if (onDeleteChat) {
                onDeleteChat(chatId);
            }

            // Navigate away if deleting current chat
            if (activeChatId === chatId) {
                navigate('/dashboard');
            }
        } catch (error) {
            console.error('Delete error:', error);
            toast.error('Failed to delete chat');
        }
    };

    // ========================================================================
    // BACKEND INTEGRATION - Create New Chat
    // ========================================================================

    const handleNewChat = async () => {
        setIsLoading(true);
        try {
            const response = await api.chat.send('Hello', null);
            const conversationId = response.data.conversation_id;
            
            toast.success('New chat created');
            navigate(`/dashboard/chats/${conversationId}`);
        } catch (error) {
            console.error('Create chat error:', error);
            toast.error('Failed to create chat');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <aside className={`sidebar${isExpanded ? ' expanded' : ' collapsed'}`}>
            <nav className="h-full flex flex-col bg-white border-r shadow-sm">
                {/* Header */}
                <div className="p-4 pb-2 flex justify-between items-center sidebar-header">
                    <img
                        src="/logo.png"
                        className={`overflow-hidden transition-all ${isExpanded ? "w-32" : "w-0"}`}
                        alt="SpectraAI"
                    />
                    <button
                        onClick={onToggle}
                        className="p-1.5 rounded-lg bg-gray-50 hover:bg-gray-100 sidebar-toggle-button"
                        title={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
                    >
                        {isExpanded ? <ChevronLeft /> : <ChevronRight />}
                    </button>
                </div>

                {/* New Chat Button */}
                <div className="px-3 pt-2">
                    <button
                        onClick={handleNewChat}
                        disabled={isLoading}
                        className={`
                            w-full flex items-center justify-center gap-2 py-2 px-3
                            bg-indigo-600 text-white rounded-md
                            hover:bg-indigo-700 transition-colors
                            disabled:opacity-50 disabled:cursor-not-allowed
                        `}
                    >
                        <Plus size={20} />
                        <span className={`transition-all ${isExpanded ? "inline" : "hidden"}`}>
                            {isLoading ? 'Creating...' : 'New Chat'}
                        </span>
                    </button>
                </div>

                {/* Navigation Items */}
                <ul className="px-3 pt-2">
                    <NavItem
                        icon={<LayoutDashboard size={20} />}
                        text="Dashboard"
                        isExpanded={isExpanded}
                        active={location.pathname === '/dashboard'}
                        to="/dashboard"
                    />
                </ul>

                {/* Search */}
                <div className="px-3 pt-2">
                    <div className="sidebar-search-chat">
                        <Search size={20} />
                        <input
                            type="text"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            placeholder="Search chats"
                            className={`sidebar-text ${isExpanded ? "" : "hidden"}`}
                        />
                    </div>
                </div>

                {/* Recent Chats List */}
                <div className="flex-1 overflow-y-auto px-3 pt-2">
                    <div className={`text-xs font-semibold text-gray-500 mb-2 ${isExpanded ? "" : "hidden"}`}>
                        RECENT CHATS
                    </div>
                    <ul className="recent-chats-list">
                        {filteredChats.length === 0 ? (
                            <li className={`text-sm text-gray-400 text-center py-4 ${isExpanded ? "" : "hidden"}`}>
                                {search ? 'No chats found' : 'No chats yet'}
                            </li>
                        ) : (
                            filteredChats.map(chat => (
                                <ChatItem
                                    key={chat.conversation_id}
                                    chat={chat}
                                    isExpanded={isExpanded}
                                    isActive={activeChatId === chat.conversation_id}
                                    onDelete={handleDeleteChat}
                                />
                            ))
                        )}
                    </ul>
                </div>

                {/* Footer / User Info */}
                <div className="border-t flex p-3 sidebar-footer">
                    <img
                        src={user?.imageUrl || `https://ui-avatars.com/api/?background=c7d2fe&color=3730a3&bold=true&name=${user?.firstName?.[0] || 'U'}`}
                        className="w-10 h-10 rounded-md"
                        alt="user avatar"
                    />
                    <div className={`flex justify-between items-center overflow-hidden transition-all ${isExpanded ? "w-52 ml-3" : "w-0"}`}>
                        <div className="leading-4">
                            <h4 className="font-semibold">
                                {user?.firstName || 'User'}
                            </h4>
                            <span className="text-xs text-gray-600">
                                {user?.primaryEmailAddress?.emailAddress || ''}
                            </span>
                        </div>
                        <Link to="/settings">
                            <Settings size={20} className="cursor-pointer hover:text-indigo-600" />
                        </Link>
                    </div>
                </div>
            </nav>
        </aside>
    );
}

Sidebar.propTypes = {
    isExpanded: PropTypes.bool.isRequired,
    onToggle: PropTypes.func.isRequired,
    recentChats: PropTypes.array.isRequired,
    onDeleteChat: PropTypes.func,
};
