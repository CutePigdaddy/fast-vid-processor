'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Upload, 
  FileVideo, 
  CheckCircle2, 
  Loader2, 
  PlayCircle, 
  AlertCircle, 
  Menu,
  X,
  Plus,
  Trash2,
  Edit2,
  Check,
  VideoOff
} from 'lucide-react';

// --- 配置区域 ---

const MOCK_MODE = false; 

const API_BASE_URL = 'http://localhost:8000';
const LOCAL_STORAGE_KEY = 'video_asr_tasks_v2';

// --- 类型定义 ---

interface TaskResult {
  text_content: string;
  duration?: number;
}

interface VideoTask {
  id: string;           // 内部临时 ID（上传前）或 file_hash（上传后）
  fileHash: string;     // 文件的 SHA-256 哈希值（核心标识）
  name: string;         // 显示名称（原始文件名）
  file: File | null;
  previewUrl: string;
  status: 'hashing' | 'uploading' | 'pending' | 'processing' | 'success' | 'error';
  progress: number;     // 0-100
  result: TaskResult | null;
  createdAt: number;
}

// --- SHA-256 哈希计算 ---

async function computeFileHash(file: File): Promise<string> {
  const CHUNK_SIZE = 2 * 1024 * 1024; // 2MB 分片读取
  const fileSize = file.size;
  let offset = 0;

  // 使用 SubtleCrypto 流式计算
  // Web Crypto API 不支持增量哈希，需要读取全部内容
  // 对于大文件，分片读取到一个 ArrayBuffer
  const chunks: ArrayBuffer[] = [];

  while (offset < fileSize) {
    const slice = file.slice(offset, offset + CHUNK_SIZE);
    const buffer = await slice.arrayBuffer();
    chunks.push(buffer);
    offset += CHUNK_SIZE;
  }

  // 合并所有 chunks
  const totalLength = chunks.reduce((acc, c) => acc + c.byteLength, 0);
  const combined = new Uint8Array(totalLength);
  let pos = 0;
  for (const chunk of chunks) {
    combined.set(new Uint8Array(chunk), pos);
    pos += chunk.byteLength;
  }

  const hashBuffer = await crypto.subtle.digest('SHA-256', combined);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// --- API 服务层 ---

const apiService = {
  // 上传视频（文件名为 hash + 原始扩展名）
  uploadVideo: async (file: File, fileHash: string, onProgress?: (percent: number) => void): Promise<{ status: string; file_hash: string; task_id?: string; message?: string }> => {
    if (MOCK_MODE) {
      return new Promise((resolve) => {
        let p = 0;
        const timer = setInterval(() => {
          p += 10;
          if (onProgress) onProgress(p);
          if (p >= 100) {
            clearInterval(timer);
            resolve({ status: 'processing', file_hash: fileHash, task_id: `mock-task-${Date.now()}` });
          }
        }, 100);
      });
    }

    // 获取原始扩展名
    const ext = file.name.substring(file.name.lastIndexOf('.'));
    // 创建以 hash 命名的新 File
    const renamedFile = new File([file], `${fileHash}${ext}`, { type: file.type });

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE_URL}/tasks/text`);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            reject(new Error('Invalid JSON response'));
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      };

      xhr.onerror = () => reject(new Error('Network error during upload'));

      const formData = new FormData();
      formData.append('file', renamedFile);
      xhr.send(formData);
    });
  },

  // 通过 file_hash 查询状态
  checkStatus: async (fileHash: string): Promise<{ status: string; celery_status?: string; meta?: any; files?: any }> => {
    if (MOCK_MODE) {
      return new Promise((resolve) => {
        const storedProgress = (window as any)[`progress_${fileHash}`] || 0;
        const newProgress = Math.min(storedProgress + 20, 100);
        (window as any)[`progress_${fileHash}`] = newProgress;

        if (newProgress >= 100) {
          resolve({ status: 'success', files: { text: true, track: true, vocal: true } });
        } else {
          resolve({ status: 'progress', celery_status: 'STARTED' });
        }
      });
    }

    const res = await fetch(`${API_BASE_URL}/files/${fileHash}/status`);
    if (!res.ok) throw new Error('Status check failed');
    return await res.json();
  },

  // 获取文本内容
  getTextContent: async (fileHash: string): Promise<string> => {
    if (MOCK_MODE) {
      return "【模拟识别结果】\n这是一个模拟的视频识别文本。";
    }
    
    const res = await fetch(`${API_BASE_URL}/files/${fileHash}/text`);
    if (!res.ok) throw new Error('Failed to get text content');
    const data = await res.json();
    return data.text_content;
  }
};

// --- 组件部分 ---

export default function VideoASRApp() {
  const [tasks, setTasks] = useState<VideoTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const pollIntervals = useRef<{ [key: string]: NodeJS.Timeout }>({});

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // --- 轮询逻辑（通过 file_hash 查询） ---
  const stopPolling = useCallback((fileHash: string) => {
    if (pollIntervals.current[fileHash]) {
      clearInterval(pollIntervals.current[fileHash]);
      delete pollIntervals.current[fileHash];
    }
  }, []);

  const startPolling = useCallback((fileHash: string) => {
    if (pollIntervals.current[fileHash]) return;

    const interval = setInterval(async () => {
      try {
        const data = await apiService.checkStatus(fileHash);
        
        // 映射后端状态
        let uiStatus: VideoTask['status'];
        let progress = 50;

        if (data.status === 'success') {
          uiStatus = 'success';
          progress = 100;
        } else if (data.status === 'failed') {
          uiStatus = 'error';
          progress = 0;
        } else {
          // progress 状态 — 根据 celery_status 细分
          uiStatus = 'processing';
          const celeryStatus = data.celery_status || '';
          if (celeryStatus === 'PENDING') progress = 10;
          else if (celeryStatus === 'STARTED') progress = 20;
          else if (celeryStatus === 'separated') progress = 40;
          else if (celeryStatus === 'distracted') progress = 65;
          else if (celeryStatus === 'converted') progress = 90;
          else progress = 30;
        }

        setTasks(prev => prev.map(t => {
          if (t.fileHash !== fileHash) return t;
          
          const updatedTask = { ...t, status: uiStatus, progress };
          
          if (uiStatus === 'success' || uiStatus === 'error') {
            stopPolling(fileHash);
            if (uiStatus === 'success') {
              // 获取文本内容
              apiService.getTextContent(fileHash).then(text => {
                setTasks(prev2 => prev2.map(t2 => 
                  t2.fileHash === fileHash 
                    ? { ...t2, result: { text_content: text } } 
                    : t2
                ));
              }).catch(console.error);
              showToast(`视频 "${t.name}" 处理完成`, 'success');
            }
          }
          return updatedTask;
        }));

      } catch (error) {
        console.error("Polling error", error);
      }
    }, 2000);

    pollIntervals.current[fileHash] = interval;
  }, [stopPolling]);

  // --- 持久化逻辑 ---

  useEffect(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        const parsedTasks = JSON.parse(saved);
        setTasks(parsedTasks);
      } catch (e) {
        console.error("Failed to load tasks", e);
      }
    }
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    
    const tasksToSave = tasks.map(t => ({
      ...t,
      file: null,
      previewUrl: t.file ? t.previewUrl : '' 
    }));
    
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(tasksToSave));
  }, [tasks, isLoaded]);

  // 恢复轮询（用 fileHash 作为 key）
  useEffect(() => {
    if (!isLoaded) return;
    
    tasks.forEach(t => {
      if ((t.status === 'pending' || t.status === 'processing') && t.fileHash && !pollIntervals.current[t.fileHash]) {
        console.log(`Resuming polling for hash ${t.fileHash}`);
        startPolling(t.fileHash);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded]);

  useEffect(() => {
    return () => {
      Object.values(pollIntervals.current).forEach(clearInterval);
    };
  }, []);

  // --- 交互逻辑 ---

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // 1. 创建本地任务（显示"计算文件指纹..."）
    const tempId = `temp-${Date.now()}`;
    const newTask: VideoTask = {
      id: tempId,
      fileHash: '',
      name: file.name,
      file: file,
      previewUrl: URL.createObjectURL(file),
      status: 'hashing',
      progress: 0,
      result: null,
      createdAt: Date.now(),
    };

    setTasks(prev => [newTask, ...prev]);
    setActiveTaskId(newTask.id);

    try {
      // 2. 计算 SHA-256 哈希
      const fileHash = await computeFileHash(file);
      
      // 检查是否已有相同 hash 的任务
      const existingTask = tasks.find(t => t.fileHash === fileHash);
      if (existingTask) {
        // 移除刚创建的临时任务
        setTasks(prev => prev.filter(t => t.id !== tempId));
        setActiveTaskId(existingTask.id);
        showToast('该文件已存在于任务列表中', 'success');
        return;
      }

      // 更新哈希值，切换到上传状态
      setTasks(prev => prev.map(t => 
        t.id === tempId ? { ...t, fileHash, id: fileHash, status: 'uploading' } : t
      ));
      setActiveTaskId(fileHash);

      // 3. 上传文件（文件名为 hash + ext）
      const response = await apiService.uploadVideo(file, fileHash, (percent) => {
        setTasks(prev => prev.map(t => 
          t.fileHash === fileHash ? { ...t, progress: percent } : t
        ));
      });

      // 4. 根据后端响应处理
      if (response.status === 'completed') {
        // 已处理过 → 直接标记成功并获取文本
        setTasks(prev => prev.map(t => 
          t.fileHash === fileHash ? { ...t, status: 'success', progress: 100 } : t
        ));
        
        apiService.getTextContent(fileHash).then(text => {
          setTasks(prev => prev.map(t => 
            t.fileHash === fileHash ? { ...t, result: { text_content: text } } : t
          ));
        }).catch(console.error);
        
        showToast('该文件已处理过，直接返回结果', 'success');
      } else {
        // processing → 开始轮询
        setTasks(prev => prev.map(t => 
          t.fileHash === fileHash ? { ...t, status: 'processing', progress: 0 } : t
        ));
        startPolling(fileHash);
        showToast('视频上传成功，开始处理...', 'success');
      }

    } catch (error) {
      console.error(error);
      setTasks(prev => prev.map(t => 
        t.id === tempId || t.fileHash === '' ? { ...t, status: 'error' } : t
      ));
      showToast('操作失败，请检查后端服务', 'error');
    }
  };

  // 删除任务
  const deleteTask = (e: React.MouseEvent, taskId: string, fileHash: string) => {
    e.stopPropagation();
    
    setTasks(prev => prev.filter(t => t.id !== taskId));
    if (fileHash) stopPolling(fileHash);

    if (activeTaskId === taskId) {
      setActiveTaskId(null);
    }
    showToast('记录已删除', 'success');
  };

  // 开始编辑
  const startEditing = (e: React.MouseEvent, task: VideoTask) => {
    e.stopPropagation();
    setEditingTaskId(task.id);
    setEditingName(task.name);
  };

  // 保存重命名
  const saveRename = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!editingName.trim()) return;

    setTasks(prev => prev.map(t => 
      t.id === editingTaskId ? { ...t, name: editingName } : t
    ));
    setEditingTaskId(null);
    showToast('重命名成功', 'success');
  };

  // 取消编辑
  const cancelEditing = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEditingTaskId(null);
  };

  // --- 渲染辅助函数 ---

  const activeTask = tasks.find(t => t.id === activeTaskId);

  return (
    <div className="flex h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
      
      {/* --- 左侧侧边栏 --- */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-xl z-20">
        <div className="p-6 border-b border-slate-700 flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <PlayCircle className="text-white w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-white tracking-wide">VideoASR</h1>
        </div>

        <nav className="flex-1 overflow-y-auto py-4">
          <div className="px-4 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Actions
          </div>
          <button
            onClick={() => setActiveTaskId(null)}
            className={`w-full flex items-center px-6 py-3 transition-colors ${
              activeTaskId === null 
                ? 'bg-blue-600 text-white' 
                : 'hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Plus className="w-5 h-5 mr-3" />
            添加视频
          </button>

          <div className="px-4 mt-8 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            History
          </div>
          <ul className="space-y-1">
            {tasks.map(task => (
              <li key={task.id} className="group relative">
                {editingTaskId === task.id ? (
                  // 编辑模式
                  <div className="w-full flex items-center px-3 py-2 bg-slate-800 border-l-4 border-blue-500">
                    <input 
                      aria-label="编辑视频名称"
                      value={editingName} 
                      onChange={(e) => setEditingName(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => {
                        if(e.key === 'Enter') saveRename();
                        if(e.key === 'Escape') cancelEditing();
                      }}
                      className="bg-slate-700 text-white text-sm rounded px-2 py-1 flex-1 min-w-0 outline-none border border-slate-600 focus:border-blue-500" 
                      autoFocus 
                    />
                    <div className="flex items-center ml-2 space-x-1">
                      <button 
                        onClick={saveRename} 
                        className="p-1 hover:text-green-400 text-slate-400"
                        title="确认修改"
                        aria-label="确认修改"
                      >
                        <Check size={16}/>
                      </button>
                      <button 
                        onClick={cancelEditing} 
                        className="p-1 hover:text-gray-200 text-slate-500"
                        title="取消修改"
                        aria-label="取消修改"
                      >
                        <X size={16}/>
                      </button>
                    </div>
                  </div>
                ) : (
                  // 正常模式
                  <>
                    <button
                      onClick={() => setActiveTaskId(task.id)}
                      className={`w-full flex items-center px-6 py-3 text-sm transition-all border-l-4 pr-16 ${
                        activeTaskId === task.id
                          ? 'border-blue-500 bg-slate-800 text-white'
                          : 'border-transparent hover:bg-slate-800 hover:text-white'
                      }`}
                    >
                      <FileVideo className="w-4 h-4 mr-3 opacity-70 shrink-0" />
                      <span className="truncate flex-1 text-left">{task.name}</span>
                      
                      {/* 状态小图标 (常驻) */}
                      <div className="ml-2 group-hover:opacity-0 transition-opacity">
                        {task.status === 'success' && <CheckCircle2 className="w-3 h-3 text-green-400" />}
                        {task.status === 'hashing' && <Loader2 className="w-3 h-3 text-yellow-400 animate-spin" />}
                        {task.status === 'processing' && <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />}
                        {task.status === 'error' && <AlertCircle className="w-3 h-3 text-red-400" />}
                      </div>
                    </button>

                    {/* 操作按钮 (Hover时显示) */}
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900/90 shadow-lg rounded px-1.5 py-1">
                      <button 
                        onClick={(e) => startEditing(e, task)} 
                        className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-slate-800 rounded transition-colors"
                        title="重命名"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button 
                        onClick={(e) => deleteTask(e, task.id, task.fileHash)} 
                        className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded transition-colors"
                        title="删除"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </>
                )}
              </li>
            ))}
            {tasks.length === 0 && (
              <li className="px-6 py-4 text-sm text-slate-600 italic">
                暂无历史记录
              </li>
            )}
          </ul>
        </nav>

        <div className="p-4 border-t border-slate-700 text-xs text-slate-500 text-center">
          Backend Status: {MOCK_MODE ? 'Mock Mode' : 'Connected'}
        </div>
      </aside>

      {/* --- 右侧主内容区 --- */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        
        {/* 自定义 Toast 提示 */}
        {toast && (
          <div className={`absolute top-6 right-6 px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2 animate-in slide-in-from-top-5 z-50 ${
            toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
          }`}>
            {toast.type === 'success' ? <CheckCircle2 size={18}/> : <AlertCircle size={18}/>}
            <span className="font-medium">{toast.msg}</span>
          </div>
        )}

        {/* 1. 添加视频页面 */}
        {activeTaskId === null && (
          <div className="flex-1 flex flex-col items-center justify-center p-10 bg-gray-50">
            <div className="max-w-xl w-full bg-white rounded-2xl shadow-sm border border-gray-200 p-10 text-center">
              <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-6">
                <Upload className="w-10 h-10 text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">上传视频进行识别</h2>
              <p className="text-gray-500 mb-8">支持 MP4, MOV, AVI 等格式。系统将自动提取音频并转换为文本。</p>
              
              <label className="relative inline-flex items-center justify-center px-8 py-4 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 cursor-pointer transition-transform hover:scale-105 active:scale-95 shadow-md group overflow-hidden">
                <span className="relative z-10 flex items-center">
                  <Plus className="w-5 h-5 mr-2" />
                  选择文件
                </span>
                <input 
                  type="file" 
                  accept="video/*" 
                  className="hidden" 
                  onChange={handleFileUpload}
                />
              </label>
            </div>
          </div>
        )}

        {/* 2. 视频详情与结果页面 */}
        {activeTask && (
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* 顶部标题栏 */}
            <header className="bg-white border-b border-gray-200 px-8 py-5 flex justify-between items-center shadow-sm">
              <div>
                <h2 className="text-xl font-bold text-gray-800 flex items-center">
                  {activeTask.name}
                  <span className={`ml-4 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    activeTask.status === 'success' ? 'bg-green-100 text-green-800' :
                    activeTask.status === 'error' ? 'bg-red-100 text-red-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {activeTask.status.toUpperCase()}
                  </span>
                </h2>
                <p className="text-xs text-gray-400 mt-1">Hash: {activeTask.fileHash ? `${activeTask.fileHash.substring(0, 16)}...` : '计算中...'}</p>
              </div>
            </header>

            {/* 内容滚动区 */}
            <div className="flex-1 overflow-y-auto p-8">
              <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
                
                {/* 左侧：视频预览与进度 */}
                <div className="flex flex-col space-y-6">
                  <div className="bg-black rounded-xl overflow-hidden shadow-lg aspect-video relative group flex items-center justify-center bg-slate-900">
                    {activeTask.previewUrl ? (
                        <video 
                          src={activeTask.previewUrl} 
                          controls 
                          className="w-full h-full object-contain"
                        />
                    ) : (
                        <div className="text-slate-500 flex flex-col items-center p-8">
                            <VideoOff className="w-12 h-12 mb-2 opacity-50"/>
                            <p className="text-sm">本地预览已失效</p>
                            <p className="text-xs opacity-60 mt-1">(刷新页面后无法访问本地临时文件)</p>
                        </div>
                    )}
                  </div>

                  {/* 进度卡片 */}
                  {(activeTask.status === 'hashing' || activeTask.status === 'uploading' || activeTask.status === 'pending' || activeTask.status === 'processing') && (
                    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-semibold text-gray-700">处理进度</span>
                        <span className="text-sm font-bold text-blue-600">{activeTask.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                        {/* 使用 CSS 变量动态控制进度条宽度 */}
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out relative w-[var(--progress-width)]" 
                          style={{ '--progress-width': `${activeTask.progress}%` } as React.CSSProperties}
                        >
                           <div className="absolute top-0 left-0 bottom-0 right-0 bg-white/30 animate-pulse"></div>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-3 flex items-center">
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        {activeTask.status === 'hashing' ? '正在计算文件指纹...' : 
                         activeTask.status === 'uploading' ? '正在上传文件...' :
                         '正在进行音轨提取与语音转文字处理...'}
                      </p>
                    </div>
                  )}

                  {/* 错误显示 */}
                  {activeTask.status === 'error' && (
                     <div className="bg-red-50 p-6 rounded-xl border border-red-100 text-red-700 flex items-start">
                        <AlertCircle className="w-6 h-6 mr-3 mt-0.5" />
                        <div>
                          <h4 className="font-bold">处理失败</h4>
                          <p className="text-sm mt-1">服务器遇到错误，请稍后重试或检查视频格式。</p>
                        </div>
                     </div>
                  )}
                </div>

                {/* 右侧：识别结果 */}
                <div className="flex flex-col h-full min-h-[400px]">
                  <div className="flex-1 bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                      <h3 className="font-semibold text-gray-700 flex items-center">
                        <FileVideo className="w-4 h-4 mr-2" />
                        识别文本
                      </h3>
                      {activeTask.result?.duration && (
                        <span className="text-xs bg-gray-200 text-gray-600 px-2 py-1 rounded">
                          时长: {activeTask.result.duration}s
                        </span>
                      )}
                    </div>
                    
                    <div className="flex-1 p-6 overflow-y-auto bg-white">
                      {activeTask.status === 'success' && activeTask.result ? (
                        <div className="prose prose-slate max-w-none">
                          <p className="whitespace-pre-wrap leading-relaxed text-gray-700">
                            {activeTask.result.text_content}
                          </p>
                        </div>
                      ) : activeTask.status === 'error' ? (
                         <div className="h-full flex flex-col items-center justify-center text-gray-300">
                            <X className="w-12 h-12 mb-2" />
                            <p>无法显示结果</p>
                        </div>
                      ) : (
                        <div className="h-full flex flex-col items-center justify-center text-gray-300">
                          <Loader2 className="w-10 h-10 mb-4 animate-spin opacity-50" />
                          <p>等待处理结果...</p>
                        </div>
                      )}
                    </div>
                    
                    {activeTask.status === 'success' && (
                        <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end space-x-3">
                            <button 
                              onClick={() => {
                                const link = document.createElement('a');
                                link.href = `${API_BASE_URL}/files/${activeTask.fileHash}/download/text`;
                                link.download = `text_${activeTask.name.replace(/\.[^.]+$/, '')}.txt`;
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                                showToast('开始下载文本文件', 'success');
                              }}
                              className="text-sm text-green-600 hover:text-green-800 font-medium px-4 py-2 hover:bg-green-50 rounded-lg transition-colors flex items-center"
                            >
                              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                              </svg>
                              下载文本
                            </button>
                            <button 
                              onClick={() => {
                                const link = document.createElement('a');
                                link.href = `${API_BASE_URL}/files/${activeTask.fileHash}/download/track`;
                                link.download = `track_${activeTask.name.replace(/\.[^.]+$/, '')}.mp3`;
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                                showToast('开始下载音轨文件', 'success');
                              }}
                              className="text-sm text-blue-600 hover:text-blue-800 font-medium px-4 py-2 hover:bg-blue-50 rounded-lg transition-colors">
                                下载音轨
                            </button>
                        </div>
                    )}
                  </div>
                </div>

              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}