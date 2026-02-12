'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Upload, FileVideo, CheckCircle2, Loader2, PlayCircle, AlertCircle, 
  Menu, X, Plus, Trash2, Edit2, Check, VideoOff, FileText, 
  Music, Film, BrainCircuit, Download, Copy, ChevronRight
} from 'lucide-react';
import SparkMD5 from 'spark-md5';

// --- 配置区域 ---

const MOCK_MODE = false; 
const API_BASE_URL = 'http://localhost:8080';
const LOCAL_STORAGE_KEY = 'video_asr_tasks_v3';

// --- 类型定义 ---

type TaskType = 'extract_audio' | 'transcribe' | 'ai_summarize' | 'extract_keyframes';

interface TaskConfig {
  extract_audio: boolean;
  transcribe: boolean;
  ai_summarize: boolean;
  extract_keyframes: boolean;
}

interface SubTaskInfo {
  taskId: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped';
  resultPath?: string;
  updatedAt?: number;
}

interface VideoTask {
  id: string;           // fileHash
  fileHash: string;
  name: string;
  file: File | null;
  previewUrl: string;
  // 总体状态
  status: 'hashing' | 'config' | 'uploading' | 'processing' | 'success' | 'error' | 'partial_success'; 
  progress: number;     // 0-100
  // 任务配置
  config: TaskConfig;
  // 子任务状态 map
  subTasks: Record<string, SubTaskInfo>; 
  createdAt: number;
}

// --- MD5 哈希计算 ---

async function computeFileHash(file: File): Promise<string> {
  // Mock 模式下快速返回，避免大文件卡顿
  if (MOCK_MODE) {
    return new Promise(resolve => setTimeout(() => resolve(`mock-hash-${Date.now()}`), 500));
  }

  const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
  const spark = new SparkMD5.ArrayBuffer();
  let offset = 0;

  while (offset < file.size) {
    const slice = file.slice(offset, offset + CHUNK_SIZE);
    const buffer = await slice.arrayBuffer();
    spark.append(buffer);
    offset += CHUNK_SIZE;
  }
  
  return spark.end();
}

// --- Mock Store (用于模拟后端状态随时间变化) ---
const mockStore: Record<string, number> = {}; // fileHash -> startTime

// --- API 服务层 ---

const apiService = {
  // 1. 上传并创建任务
  createTask: async (
    file: File, 
    fileHash: string, 
    config: TaskConfig,
    onProgress?: (percent: number) => void
  ): Promise<{ status: string; tasks: { task_name: string; task_id: string }[] }> => {
    
    if (MOCK_MODE) {
      // 模拟上传进度
      return new Promise((resolve) => {
        let p = 0;
        const interval = setInterval(() => {
          p += 20;
          if (onProgress) onProgress(p);
          if (p >= 100) {
            clearInterval(interval);
            // 初始化 Mock 开始时间
            mockStore[fileHash] = Date.now();
            
            // 构建返回的任务列表
            const mockTasks = [];
            if (config.extract_audio) mockTasks.push({ task_name: 'extract_audio', task_id: `mock-audio-${fileHash}` });
            if (config.transcribe) mockTasks.push({ task_name: 'transcribe', task_id: `mock-asr-${fileHash}` }); // 注意：后端 api.py 中名为 'asr' 但数据库记录可能不同，这里为了匹配前端 TaskType 映射，我们假设后端返回 task_name 与前端 TaskType 一致，或者在前端做了映射。根据 api.py response_tasks，后端返回的是 "extract_audio", "asr", "ai_summarize", "extract_keyframes"。
            // 前端需要处理 'asr' -> 'transcribe' 的映射，或者我们在 Mock 数据里直接返回 'transcribe' 方便（如果后端逻辑允许）。
            // 这里为了严谨，我们模拟后端 api.py 的行为返回 'asr'，并在前端处理映射。
            if (config.transcribe) mockTasks.push({ task_name: 'asr', task_id: `mock-asr-${fileHash}` });
            if (config.ai_summarize) mockTasks.push({ task_name: 'ai_summarize', task_id: `mock-ai-${fileHash}` });
            if (config.extract_keyframes) mockTasks.push({ task_name: 'extract_keyframes', task_id: `mock-kf-${fileHash}` });

            resolve({ status: 'processing', tasks: mockTasks });
          }
        }, 200);
      });
    }

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE_URL}/tasks/${fileHash}`);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) { reject(new Error('Invalid JSON')); }
        } else {
          reject(new Error(xhr.responseText || 'Upload failed'));
        }
      };
      xhr.onerror = () => reject(new Error('Network Error'));

      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_hash', fileHash);
      formData.append('extract_audio', config.extract_audio.toString());
      formData.append('transcribe', config.transcribe.toString());
      formData.append('ai_summarize', config.ai_summarize.toString());
      formData.append('extract_keyframes', config.extract_keyframes.toString());

      xhr.send(formData);
    });
  },

  // 2. 获取文件总体进度 /status/{file_hash}
  getFileStatus: async (fileHash: string) => {
    if (MOCK_MODE) {
      const startTime = mockStore[fileHash];
      if (!startTime) return {};

      const now = Date.now();
      const elapsed = (now - startTime) / 1000; // 秒

      // 模拟各个阶段的状态
      // 0-3s: 音轨提取中
      // 3-6s: 音轨完成，转写中
      // 6-9s: 转写完成，摘要中
      // 9s+: 全部完成
      
      const getStatus = (startSec: number, duration: number) => {
        if (elapsed < startSec) return 'pending';
        if (elapsed < startSec + duration) return 'running';
        return 'success';
      };

      return {
        extract_audio: {
          status: getStatus(0, 3),
          task_id: `mock-audio-${fileHash}`,
          result_path: '/mock/audio.mp3',
          completed_at: new Date().toISOString()
        },
        transcribe: {
          status: getStatus(3, 3),
          task_id: `mock-asr-${fileHash}`,
          result_path: '/mock/transcript.txt',
          completed_at: new Date().toISOString()
        },
        ai_summarize: {
          status: getStatus(6, 3),
          task_id: `mock-ai-${fileHash}`,
          result_path: '/mock/summary.md',
          completed_at: new Date().toISOString()
        },
        extract_keyframes: {
          status: getStatus(0, 5), // 并行任务
          task_id: `mock-kf-${fileHash}`,
          result_path: '/mock/keyframes.zip',
          completed_at: new Date().toISOString()
        }
      };
    }

    const res = await fetch(`${API_BASE_URL}/status/${fileHash}`);
    if (!res.ok) throw new Error('Failed to fetch file status');
    return res.json();
  },

  // 3. 获取单个任务详细状态 /tasks/{task_id}/status
  getTaskStatus: async (taskId: string) => {
    if (MOCK_MODE) {
      // 这里的 taskId 格式是 mock-type-hash
      // 简单返回 success，实际逻辑由 getFileStatus 控制大流程
      return {
        task_id: taskId,
        status: 'success',
        created_at: new Date(Date.now() - 10000).toISOString(),
        started_at: new Date(Date.now() - 8000).toISOString(),
        completed_at: new Date(Date.now() - 2000).toISOString(),
        result_path: '/mock/result/path',
        error_message: null
      };
    }
    const res = await fetch(`${API_BASE_URL}/tasks/${taskId}/status`);
    if (!res.ok) throw new Error('Failed to fetch task status');
    return res.json();
  },

  // 4. 获取文本内容 /files/{file_hash}/text
  getTextContent: async (fileHash: string) => {
    if (MOCK_MODE) {
      return { 
        file_hash: fileHash,
        text_content: `【模拟转写结果 - ${fileHash}】\n\n[00:00.00] 这是一个演示视频的语音转写内容。\n[00:05.20] 我们正在测试前端与后端的接口对接情况。\n[00:10.50] Mock 模式下，你可以看到完整的 UI 交互流程，而无需启动 Docker 后端。\n[00:15.00] 这是一个 AI 生成的摘要：\n本视频主要演示了 VideoASR 系统的处理流程，展示了从文件上传、哈希计算、任务配置到最终结果展示的完整链路。系统运行稳定，UI 响应迅速。` 
      };
    }
    const res = await fetch(`${API_BASE_URL}/files/${fileHash}/text`);
    if (!res.ok) throw new Error('Failed to fetch text content');
    return res.json();
  },

  // 5. 下载文件链接生成
  getDownloadUrl: (taskId: string) => {
    if (MOCK_MODE) return '#';
    return `${API_BASE_URL}/files/${taskId}`;
  }
};

// --- 组件部分 ---

export default function VideoASRApp() {
  const [tasks, setTasks] = useState<VideoTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null); // null = upload page, string = hash
  const [activeSubTab, setActiveSubTab] = useState<TaskType | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  
  // 上传配置相关状态
  const [uploadStep, setUploadStep] = useState<'select' | 'config' | 'hashing' | 'uploading'>('select');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [tempConfig, setTempConfig] = useState<TaskConfig>({
    extract_audio: true,
    transcribe: true,
    ai_summarize: true,
    extract_keyframes: false
  });

  // 编辑重命名相关
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const pollIntervals = useRef<{ [key: string]: NodeJS.Timeout }>({});

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // --- 轮询逻辑 ---
  
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
        // 1. 获取后端该文件的所有子任务状态 map
        const statusMap = await apiService.getFileStatus(fileHash);
        
        setTasks(prev => prev.map(t => {
          if (t.fileHash !== fileHash) return t;

          const newSubTasks = { ...t.subTasks };
          let allSuccess = true;
          let anyRunning = false;
          let anyFailed = false;

          // 遍历配置中开启的任务
          const activeTaskKeys = Object.keys(t.config).filter(k => t.config[k as TaskType]);
          
          activeTaskKeys.forEach(key => {
            // 注意：处理后端 task_name 与前端 key 的映射
            // api.py 返回 'asr'，前端使用 'transcribe'
            const backendKey = key === 'transcribe' ? 'asr' : key; // 简单的映射逻辑
            
            // 尝试直接获取，如果后端返回了 'transcribe' 则直接用，否则尝试 'asr'
            const backendInfo = statusMap[key] || statusMap['asr']; 

            if (backendInfo) {
              // 更新子任务状态
              if (newSubTasks[key]) {
                newSubTasks[key] = { 
                  ...newSubTasks[key], 
                  status: backendInfo.status,
                  resultPath: backendInfo.result_path 
                };
              } else {
                // 如果之前没存（比如页面刷新了），补录
                newSubTasks[key] = { 
                  taskId: backendInfo.task_id, 
                  status: backendInfo.status,
                  resultPath: backendInfo.result_path 
                };
              }
            }
          });

          // 计算总体进度
          let completedCount = 0;
          activeTaskKeys.forEach(key => {
            const s = newSubTasks[key]?.status;
            if (s === 'success') completedCount++;
            else if (s === 'failed') anyFailed = true;
            else if (s === 'pending' || s === 'running') anyRunning = true;
            else allSuccess = false; // missing or other
          });

          const totalActive = activeTaskKeys.length;
          const progress = totalActive === 0 ? 0 : Math.round((completedCount / totalActive) * 100);
          
          let overallStatus: VideoTask['status'] = t.status;
          
          if (completedCount === totalActive) overallStatus = 'success';
          else if (anyFailed && !anyRunning) overallStatus = 'partial_success'; // 部分失败但没在跑了
          else if (anyRunning) overallStatus = 'processing';
          
          // 如果全部完成或全部停止，结束轮询
          if (completedCount === totalActive || (anyFailed && !anyRunning)) {
             stopPolling(fileHash);
          }

          return {
            ...t,
            status: overallStatus,
            progress: progress,
            subTasks: newSubTasks
          };
        }));

      } catch (error) {
        console.error(`Polling error for ${fileHash}`, error);
      }
    }, 1000); // Mock 模式下加快轮询频率，实际可用 3000

    pollIntervals.current[fileHash] = interval;
  }, [stopPolling]);

  // --- 持久化 ---
  useEffect(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setTasks(parsed);
      } catch(e) { console.error(e); }
    }
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    const toSave = tasks.map(t => ({
      ...t,
      file: null,
      previewUrl: t.file ? t.previewUrl : '' // 注意：刷新后 blob url 会失效
    }));
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(toSave));
  }, [tasks, isLoaded]);

  // 恢复轮询
  useEffect(() => {
    if(!isLoaded) return;
    tasks.forEach(t => {
      if (t.status === 'processing' || t.status === 'uploading') {
         startPolling(t.fileHash);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded]);

  // 清理轮询
  useEffect(() => {
    return () => {
      Object.values(pollIntervals.current).forEach(clearInterval);
    };
  }, []);

  // --- 交互处理 ---

  // 1. 文件选择
  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setUploadStep('config');
  };

  // 2. 确认配置并上传
  const startUploadProcess = async () => {
    if (!selectedFile) return;
    
    setUploadStep('hashing');
    
    // 生成临时任务以防 UI 闪烁
    const tempHash = await computeFileHash(selectedFile);
    
    // 检查重复
    const exist = tasks.find(t => t.fileHash === tempHash);
    if (exist) {
      showToast('任务已存在', 'success');
      setActiveTaskId(tempHash);
      setUploadStep('select');
      setSelectedFile(null);
      return;
    }

    const newTask: VideoTask = {
      id: tempHash,
      fileHash: tempHash,
      name: selectedFile.name,
      file: selectedFile,
      previewUrl: URL.createObjectURL(selectedFile),
      status: 'uploading',
      progress: 0,
      config: { ...tempConfig },
      subTasks: {},
      createdAt: Date.now()
    };

    setTasks(prev => [newTask, ...prev]);
    setActiveTaskId(tempHash);
    setUploadStep('select'); // 重置上传页状态
    setSelectedFile(null);

    // 开始上传
    try {
      const res = await apiService.createTask(
        newTask.file!, // 修复1：添加非空断言，因为我们已确认 selectedFile 存在
        tempHash, 
        newTask.config,
        (pct) => setTasks(prev => prev.map(t => t.fileHash === tempHash ? { ...t, progress: pct } : t))
      );

      // 上传成功，初始化 subTasks
      const initSubTasks: Record<string, SubTaskInfo> = {};
      res.tasks.forEach(item => {
        // 后端返回的 task_name 可能与前端不同 (如 asr)，这里做简单的映射存储
        let key = item.task_name;
        if (key === 'asr') key = 'transcribe';
        
        initSubTasks[key] = {
          taskId: item.task_id,
          status: 'pending'
        };
      });

      setTasks(prev => prev.map(t => t.fileHash === tempHash ? {
        ...t,
        status: 'processing',
        progress: 0, // 重置进度条为处理进度
        subTasks: initSubTasks
      } : t));

      // 开启轮询
      startPolling(tempHash);
      showToast('上传成功，开始处理', 'success');

    } catch (e) {
      console.error(e);
      setTasks(prev => prev.map(t => t.fileHash === tempHash ? { ...t, status: 'error' } : t));
      showToast('上传失败', 'error');
    }
  };

  const handleConfigChange = (key: keyof TaskConfig) => {
    setTempConfig(prev => {
      const next = { ...prev, [key]: !prev[key] };
      // 依赖关系：AI摘要 必须开启 转写
      if (key === 'ai_summarize' && next.ai_summarize) {
        next.transcribe = true;
      }
      // 依赖关系：关闭 转写 必须关闭 AI摘要
      if (key === 'transcribe' && !next.transcribe) {
        next.ai_summarize = false;
      }
      return next;
    });
  };

  // --- 子组件渲染 ---

  // 渲染次级菜单的内容
  const SubTaskViewer = ({ task, type }: { task: VideoTask, type: TaskType }) => {
    const subTask = task.subTasks[type];
    const [detailStatus, setDetailStatus] = useState<any>(null);
    const [textContent, setTextContent] = useState<string>('');
    const [loading, setLoading] = useState(false);

    // 当 tab 切换或状态变为 success 时获取详情
    useEffect(() => {
      if (!subTask) return;
      
      const fetchDetail = async () => {
        setLoading(true);
        try {
          // 获取任务详细状态
          if (subTask.taskId) {
            const statusData = await apiService.getTaskStatus(subTask.taskId);
            setDetailStatus(statusData);
          }
          
          // 如果是文本类且已完成，获取文本
          if (subTask.status === 'success') {
            if (type === 'transcribe') {
              const textData = await apiService.getTextContent(task.fileHash);
              setTextContent(textData.text_content);
            } else if (type === 'ai_summarize' && subTask.taskId) {
              // 对于 AI 总结任务，通过 taskId 获取总结结果，而不是使用文件转写文本接口
              const response = await fetch(`${API_BASE_URL}/tasks/${subTask.taskId}/result`, {
                method: 'GET',
              });
              if (!response.ok) {
                throw new Error(`Failed to fetch summary result for task ${subTask.taskId}`);
              }
              // 后端可以返回纯文本或 JSON，这里优先尝试 JSON，再回退到纯文本
              let summaryText = '';
              const contentType = response.headers.get('content-type') || '';
              if (contentType.includes('application/json')) {
                const json = await response.json();
                summaryText = json.text_content || json.summary || json.result || '';
              } else {
                summaryText = await response.text();
              }
              setTextContent(summaryText);
            }
          }
        } catch (e) { console.error(e); }
        setLoading(false);
      };

      fetchDetail();
    }, [subTask?.taskId, subTask?.status, type, task.fileHash]);

    if (!subTask) return <div className="text-gray-400 p-8 text-center">该任务未初始化或未选择</div>;

    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col h-[500px]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            {type === 'extract_audio' && <Music className="w-4 h-4 text-purple-500" />}
            {type === 'transcribe' && <FileText className="w-4 h-4 text-blue-500" />}
            {type === 'ai_summarize' && <BrainCircuit className="w-4 h-4 text-orange-500" />}
            {type === 'extract_keyframes' && <Film className="w-4 h-4 text-green-500" />}
            <span className="font-semibold text-gray-700">
              {type === 'extract_audio' ? '音轨提取' : 
               type === 'transcribe' ? '语音转文字' : 
               type === 'ai_summarize' ? 'AI 智能摘要' : '关键帧提取'}
            </span>
          </div>
          <span className={`px-2 py-1 text-xs rounded-full font-medium ${
            subTask.status === 'success' ? 'bg-green-100 text-green-800' :
            subTask.status === 'running' || subTask.status === 'pending' ? 'bg-blue-100 text-blue-800' :
            'bg-red-100 text-red-800'
          }`}>
            {subTask.status.toUpperCase()}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto bg-gray-50/50">
          {loading ? (
            <div className="h-full flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : subTask.status === 'success' ? (
            <>
              {/* 文本展示 */}
              {(type === 'transcribe' || type === 'ai_summarize') && (
                <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700 leading-relaxed">
                    {textContent || "暂无内容..."}
                  </pre>
                </div>
              )}
              
              {/* 文件下载提示 */}
              {(type === 'extract_audio' || type === 'extract_keyframes') && (
                <div className="h-full flex flex-col items-center justify-center text-gray-500">
                  <CheckCircle2 className="w-16 h-16 text-green-500 mb-4 opacity-20" />
                  <p>文件处理完成，请点击下方按钮下载</p>
                </div>
              )}
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              {subTask.status === 'failed' ? <AlertCircle className="w-10 h-10 mb-2 text-red-300" /> : <Loader2 className="w-10 h-10 mb-2 animate-spin" />}
              <p>{subTask.status === 'failed' ? '任务处理失败' : '任务正在排队或处理中...'}</p>
              {detailStatus?.error_message && <p className="text-red-500 text-xs mt-2">{detailStatus.error_message}</p>}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {subTask.status === 'success' && (
          <div className="p-4 border-t border-gray-100 bg-white flex justify-end space-x-3">
            {(type === 'transcribe' || type === 'ai_summarize') && (
              <button 
                onClick={() => {
                   navigator.clipboard.writeText(textContent);
                   showToast('文本已复制', 'success');
                }}
                className="flex items-center px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <Copy className="w-4 h-4 mr-2" />
                复制文本
              </button>
            )}
            
            {/* 所有类型如果 task_id 有效都可以尝试下载 (文本下载txt, 音频下载mp3等) */}
            <button 
              onClick={() => {
                const url = apiService.getDownloadUrl(subTask.taskId);
                if (MOCK_MODE) {
                  showToast('Mock模式：开始演示文件下载', 'success');
                  return;
                }
                const link = document.createElement('a');
                link.href = url;
                link.download = ''; // 让浏览器决定文件名
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
              }}
              className="flex items-center px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-colors shadow-sm"
            >
              <Download className="w-4 h-4 mr-2" />
              下载文件
            </button>
          </div>
        )}
      </div>
    );
  };

  const activeTask = tasks.find(t => t.id === activeTaskId);

  return (
    <div className="flex h-screen bg-gray-50 text-gray-800 font-sans overflow-hidden">
      
      {/* --- 左侧侧边栏 --- */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-xl z-20 shrink-0">
        <div className="p-6 border-b border-slate-700 flex items-center space-x-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <PlayCircle className="text-white w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-white tracking-wide">VideoASR</h1>
        </div>

        <nav className="flex-1 overflow-y-auto py-4">
          <button
            onClick={() => { setActiveTaskId(null); setUploadStep('select'); }}
            className={`mx-4 mb-6 flex items-center justify-center px-4 py-3 rounded-lg transition-all ${
              activeTaskId === null 
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' 
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            <Plus className="w-5 h-5 mr-2" />
            <span className="font-medium">新建任务</span>
          </button>

          <div className="px-6 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            History
          </div>
          <ul className="space-y-1">
            {tasks.map(task => (
              <li key={task.id} className="group relative">
                {editingTaskId === task.id ? (
                   // ... (原有重命名逻辑保持精简)
                   <div className="px-3 py-2 bg-slate-800 mx-2 rounded">
                      <input 
                         aria-label="重命名视频" // 修复2：添加 aria-label
                         className="bg-transparent text-white w-full text-sm outline-none"
                         autoFocus
                         value={editingName}
                         onChange={e => setEditingName(e.target.value)}
                         onKeyDown={e => {
                           if(e.key === 'Enter') {
                             setTasks(prev => prev.map(t => t.id === task.id ? {...t, name: editingName} : t));
                             setEditingTaskId(null);
                           }
                         }}
                         onBlur={() => setEditingTaskId(null)}
                      />
                   </div>
                ) : (
                  <button
                    onClick={() => setActiveTaskId(task.id)}
                    className={`w-full flex items-center px-6 py-3 text-sm transition-all border-l-4 ${
                      activeTaskId === task.id
                        ? 'border-blue-500 bg-slate-800 text-white'
                        : 'border-transparent hover:bg-slate-800/50 hover:text-white text-slate-400'
                    }`}
                  >
                    <FileVideo className={`w-4 h-4 mr-3 shrink-0 ${activeTaskId === task.id ? 'text-blue-400' : 'opacity-50'}`} />
                    <span className="truncate flex-1 text-left">{task.name}</span>
                    <div className="ml-2">
                       {task.status === 'success' && <CheckCircle2 className="w-3 h-3 text-green-400" />}
                       {task.status === 'processing' && <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />}
                       {task.status === 'error' && <AlertCircle className="w-3 h-3 text-red-400" />}
                    </div>
                  </button>
                )}
                <button 
                  aria-label="删除任务" // 修复3：添加 aria-label
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    // Stop polling for this task
                    stopPolling(task.fileHash);
                    // Revoke blob URL to free memory
                    if (task.previewUrl) {
                      URL.revokeObjectURL(task.previewUrl);
                    }
                    // Remove task from state
                    setTasks(prev => prev.filter(t => t.id !== task.id)); 
                  }}
                  className="absolute right-2 top-3 opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-slate-500 transition-opacity"
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* --- 右侧主内容区 --- */}
      <main className="flex-1 flex flex-col overflow-hidden relative bg-gray-50">
        
        {/* Toast */}
        {toast && (
          <div className={`absolute top-6 right-6 px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2 animate-in slide-in-from-top-5 z-50 ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
          }`}>
            {toast.type === 'success' ? <CheckCircle2 size={18}/> : <AlertCircle size={18}/>}
            <span className="font-medium">{toast.msg}</span>
          </div>
        )}

        {/* 1. 上传页面 */}
        {activeTaskId === null && (
          <div className="flex-1 flex flex-col items-center justify-center p-10">
            
            {uploadStep === 'select' && (
              <div className="max-w-xl w-full bg-white rounded-2xl shadow-xl border border-gray-100 p-12 text-center animate-in zoom-in-95 duration-300">
                <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Upload className="w-10 h-10 text-blue-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">上传视频</h2>
                <p className="text-gray-500 mb-8">支持 MP4, MOV, AVI 等格式</p>
                <label className="relative inline-flex items-center justify-center px-8 py-4 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 cursor-pointer shadow-lg hover:shadow-blue-500/30 transition-all transform hover:-translate-y-0.5">
                  <span className="flex items-center">
                    <Plus className="w-5 h-5 mr-2" /> 选择文件
                  </span>
                  <input type="file" accept="video/*" className="hidden" onChange={onFileSelect} />
                </label>
              </div>
            )}

            {uploadStep === 'config' && selectedFile && (
               <div className="max-w-lg w-full bg-white rounded-2xl shadow-xl border border-gray-100 p-8 animate-in slide-in-from-bottom-10">
                 <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
                   <CheckCircle2 className="w-5 h-5 mr-2 text-blue-600" />
                   处理配置
                 </h3>
                 <div className="space-y-4 mb-8">
                    <div 
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center ${tempConfig.extract_audio ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-200'}`}
                      onClick={() => handleConfigChange('extract_audio')}
                    >
                      <div className={`w-5 h-5 rounded border mr-3 flex items-center justify-center ${tempConfig.extract_audio ? 'bg-purple-500 border-purple-500' : 'border-gray-300'}`}>
                        {tempConfig.extract_audio && <Check size={12} className="text-white" />}
                      </div>
                      <div>
                        <div className="font-semibold text-gray-700">提取音轨</div>
                        <div className="text-xs text-gray-500">从视频中分离人声与背景音</div>
                      </div>
                    </div>

                    <div 
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center ${tempConfig.transcribe ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-200'}`}
                      onClick={() => handleConfigChange('transcribe')}
                    >
                      <div className={`w-5 h-5 rounded border mr-3 flex items-center justify-center ${tempConfig.transcribe ? 'bg-blue-500 border-blue-500' : 'border-gray-300'}`}>
                         {tempConfig.transcribe && <Check size={12} className="text-white" />}
                      </div>
                      <div>
                        <div className="font-semibold text-gray-700">语音转文字 (ASR)</div>
                        <div className="text-xs text-gray-500">生成逐字稿字幕</div>
                      </div>
                    </div>

                    <div 
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center ${tempConfig.ai_summarize ? 'border-orange-500 bg-orange-50' : 'border-gray-200 hover:border-orange-200'}`}
                      onClick={() => handleConfigChange('ai_summarize')}
                    >
                      <div className={`w-5 h-5 rounded border mr-3 flex items-center justify-center ${tempConfig.ai_summarize ? 'bg-orange-500 border-orange-500' : 'border-gray-300'}`}>
                         {tempConfig.ai_summarize && <Check size={12} className="text-white" />}
                      </div>
                      <div>
                        <div className="font-semibold text-gray-700">AI 智能摘要</div>
                        <div className="text-xs text-gray-500">基于转写内容生成总结 (需开启ASR)</div>
                      </div>
                    </div>

                    <div 
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex items-center ${tempConfig.extract_keyframes ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-green-200'}`}
                      onClick={() => handleConfigChange('extract_keyframes')}
                    >
                      <div className={`w-5 h-5 rounded border mr-3 flex items-center justify-center ${tempConfig.extract_keyframes ? 'bg-green-500 border-green-500' : 'border-gray-300'}`}>
                         {tempConfig.extract_keyframes && <Check size={12} className="text-white" />}
                      </div>
                      <div>
                        <div className="font-semibold text-gray-700">提取关键帧</div>
                        <div className="text-xs text-gray-500">自动截取视频精彩画面</div>
                      </div>
                    </div>
                 </div>

                 <button 
                   onClick={startUploadProcess}
                   className="w-full py-4 bg-gray-900 text-white rounded-xl font-bold hover:bg-black transition-colors flex items-center justify-center"
                 >
                   开始处理 <ChevronRight className="w-5 h-5 ml-1" />
                 </button>
               </div>
            )}

            {uploadStep === 'hashing' && (
              <div className="text-center">
                 <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
                 <h3 className="text-lg font-bold text-gray-800">正在计算文件指纹...</h3>
                 <p className="text-gray-500 text-sm mt-2">使用 MD5 生成文件标识</p>
              </div>
            )}
          </div>
        )}

        {/* 2. 详情页面 */}
        {activeTask && (
          <div className="flex flex-col h-full">
            {/* Header */}
            <header className="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shadow-sm shrink-0 z-10">
              <div>
                <h2 className="text-lg font-bold text-gray-800 flex items-center">
                  {activeTask.name}
                  <span className={`ml-3 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${
                     activeTask.status === 'success' ? 'bg-green-100 text-green-700' :
                     activeTask.status === 'processing' ? 'bg-blue-100 text-blue-700' :
                     'bg-gray-100 text-gray-600'
                  }`}>
                    {activeTask.status}
                  </span>
                </h2>
                <div className="text-xs text-gray-400 mt-1 font-mono">HASH: {activeTask.fileHash.substring(0, 16)}...</div>
              </div>
              <div className="flex items-center space-x-6">
                 {/* 总体进度条 */}
                 <div className="flex flex-col w-48">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-gray-600">Total Progress</span>
                      <span className="font-bold text-blue-600">{activeTask.progress}%</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                       <div 
                         className="h-full bg-blue-600 rounded-full transition-all duration-500"
                         style={{ width: `${activeTask.progress}%` }}
                       />
                    </div>
                 </div>
              </div>
            </header>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-8">
               <div className="max-w-6xl mx-auto space-y-8">
                  
                  {/* Video Preview */}
                  <div className="bg-black rounded-2xl overflow-hidden shadow-lg aspect-video relative group flex items-center justify-center bg-slate-900 border border-slate-800">
                    {activeTask.previewUrl ? (
                      <video src={activeTask.previewUrl} controls className="w-full h-full object-contain" />
                    ) : (
                      <div className="text-slate-500 flex flex-col items-center p-8">
                        <VideoOff className="w-12 h-12 mb-2 opacity-30"/>
                        <p className="text-sm">预览失效 (刷新导致)</p>
                      </div>
                    )}
                  </div>

                  {/* Sub-Task Tabs */}
                  <div>
                    <div className="flex space-x-1 border-b border-gray-200 mb-6">
                       {Object.keys(activeTask.config).filter(k => activeTask.config[k as TaskType]).map(key => {
                          const k = key as TaskType;
                          const subStatus = activeTask.subTasks[k]?.status;
                          return (
                            <button
                              key={k}
                              onClick={() => setActiveSubTab(k)}
                              className={`px-6 py-3 text-sm font-medium rounded-t-lg transition-all border-b-2 flex items-center ${
                                activeSubTab === k 
                                  ? 'border-blue-600 text-blue-600 bg-blue-50/50' 
                                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                              }`}
                            >
                              {/* Icon */}
                              {k === 'extract_audio' && <Music className="w-4 h-4 mr-2" />}
                              {k === 'transcribe' && <FileText className="w-4 h-4 mr-2" />}
                              {k === 'ai_summarize' && <BrainCircuit className="w-4 h-4 mr-2" />}
                              {k === 'extract_keyframes' && <Film className="w-4 h-4 mr-2" />}
                              
                              {/* Label */}
                              {k === 'extract_audio' ? '音轨' : k === 'transcribe' ? '转写' : k === 'ai_summarize' ? '摘要' : '关键帧'}
                              
                              {/* Status Dot */}
                              <span className={`ml-2 w-2 h-2 rounded-full ${
                                subStatus === 'success' ? 'bg-green-500' :
                                subStatus === 'failed' ? 'bg-red-500' :
                                subStatus === 'running' ? 'bg-blue-400 animate-pulse' :
                                'bg-gray-300'
                              }`} />
                            </button>
                          );
                       })}
                    </div>

                    {/* Sub-Task Detail View */}
                    {activeSubTab ? (
                      <SubTaskViewer task={activeTask} type={activeSubTab} />
                    ) : (
                      <div className="text-center py-12 text-gray-400 bg-white rounded-xl border border-dashed border-gray-300">
                        请选择上方的任务标签查看详情
                      </div>
                    )}
                  </div>

               </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}