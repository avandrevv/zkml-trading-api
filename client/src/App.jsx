import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API = 'http://127.0.0.1:8000';

function App() {
  const [features, setFeatures] = useState('');
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [verified, setVerified] = useState(null);
  const [history, setHistory] = useState([]);
  
  const pollInterval = useRef(null);

  const generateRandom = () => {
    const randomValues = Array.from({ length: 10 }, () => Math.floor(Math.random() * 400) + 100);
    setFeatures(randomValues.join(', '));
  };

  // Загрузка истории (последние 100 задач)
  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API}/tasks?limit=100`);
      setHistory(res.data);
    } catch (e) { 
      console.error("History error:", e); 
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const stopPolling = () => {
    if (pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
  };


  const pollTask = (id) => {
    stopPolling();
    pollInterval.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/result/${id}`);
        setStatus(res.data.status);
        fetchHistory();
        
        // Сбрасываем loading, если задача уже не в очереди
        if (res.data.status !== 'queued') {
          setLoading(false);
        }
        
        if (res.data.status === 'completed') {
          setResult(res.data.result);
          stopPolling();
        } else if (res.data.status === 'failed') {
          stopPolling();
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    }, 3000);
  };

  const submit = async () => {
    if (!features) return;
    setLoading(true);
    setResult(null);
    setVerified(null);
    setStatus('submitting');

    try {
      const featArray = features.split(',').map(num => parseFloat(num.trim()));
      const res = await axios.post(`${API}/submit`, { features: featArray });
      setTaskId(res.data.task_id);
      // setStatus(res.data.status);
      pollTask(res.data.task_id);
    } catch (e) {
      alert("Ошибка отправки");
      setLoading(false);
    }
  };

  const selectTask = (t) => {
    stopPolling();
    setTaskId(t.task_id);
    setStatus(t.status);
    setResult(typeof t.result === 'string' ? JSON.parse(t.result) : t.result);
    setVerified(null);
    setLoading(t.status === 'processing' || t.status === 'pending');
    if (t.status === 'processing' || t.status === 'pending') {
      pollTask(t.task_id);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', fontFamily: 'sans-serif', backgroundColor: '#f4f7f6', color: '#333' }}>
      
      {/* ЛЕВАЯ ПАНЕЛЬ: ВВОД */}
      <div style={{ width: '350px', padding: '25px', backgroundColor: '#fff', borderRight: '1px solid #ddd', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ marginBottom: '20px', color: '#1a1a1a' }}>🛡️ ZK ML Model</h2>
        
        <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#666', marginBottom: '8px' }}>INPUT FEATURES (X)</label>
        <input 
          value={features} 
          onChange={e => setFeatures(e.target.value)}
          placeholder="31000, 32500, ..."
          style={{ 
            padding: '12px', 
            borderRadius: '6px', 
            border: '1px solid #ccc', 
            marginBottom: '15px',
            backgroundColor: '#fff',
            color: '#000',
            fontSize: '14px'
          }}
        />
        
        <button 
          onClick={submit} 
          disabled={loading}
          style={{ 
            padding: '12px', 
            backgroundColor: loading ? '#ccc' : '#2563eb', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '6px', 
            cursor: loading ? 'default' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {loading ? 'GENERATING PROOF...' : 'GENERATE PROOF'}
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#666' }}>INPUT FEATURES (X)</label>
          <button onClick={generateRandom} style={{ fontSize: '10px', color: '#2563eb', border: 'none', background: 'none', cursor: 'pointer' }}>
            [🎲 Random]
          </button>
        </div>

        {taskId && (
          <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '11px', color: '#64748b' }}>TASK ID:</div>
            <div style={{ fontSize: '12px', wordBreak: 'break-all', fontFamily: 'monospace' }}>{taskId}</div>
            <div style={{ marginTop: '10px', fontWeight: 'bold', color: status === 'completed' ? '#059669' : '#d97706' }}>
              {/* STATUS: {status?.toUpperCase()} */}
              STATUS: {history.find(t => t.task_id === taskId)?.status?.toUpperCase() || '---'}
            </div>
          </div>
        )}
      </div>

      {/* ЦЕНТРАЛЬНАЯ ПАНЕЛЬ: РЕЗУЛЬТАТ */}
      <div style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <h3 style={{ borderBottom: '2px solid #eee', paddingBottom: '10px' }}>Verification Workspace</h3>
          
          
      {result ? (
        <div style={{ marginTop: '20px', display: 'grid', gap: '20px' }}>
          <div style={{ backgroundColor: '#fff', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
            
            {/* ИНФОРМАЦИЯ О PROOF (чёрное окно) */}
            <div style={{ 
              backgroundColor: '#1e1e1e', 
              padding: '12px 16px', 
              borderRadius: '8px', 
              marginBottom: '20px',
              fontFamily: 'monospace',
              fontSize: '13px',
              color: '#d4d4d4'
            }}>
              <strong style={{ color: '#fff' }}>Proof file:</strong> {result.proof_path}
            </div>
            
            {/* СТРОКА С КНОПКАМИ И СИГНАЛОМ */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              {/* КНОПКА ВЕРИФИКАЦИИ */}
              <button 
                onClick={async () => {
                  const res = await axios.post(`${API}/verify/${taskId}`);
                  setVerified(res.data.verified);
                }}
                style={{ 
                  padding: '10px 20px', 
                  backgroundColor: '#10b981', 
                  color: '#fff', 
                  border: 'none', 
                  borderRadius: '6px', 
                  cursor: 'pointer', 
                  fontWeight: 'bold',
                  fontSize: '14px'
                }}
              >
                RUN VERIFICATION
              </button>
              
              {/* КНОПКА СКАЧИВАНИЯ (иконка) */}
              <button 
                onClick={() => {
                  window.open(`${API}/proof/${result.proof_path}`, '_blank');
                }}
                style={{
                  padding: '10px 16px',
                  backgroundColor: '#6b7280',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title="Скачать proof"
              >
                📥
              </button>
              
              {/* СИГНАЛ BUY/SELL/HOLD */}
              {result.action && (
                <div style={{
                  padding: '8px 20px',
                  borderRadius: '6px',
                  fontWeight: 'bold',
                  fontSize: '16px',
                  textAlign: 'center',
                  minWidth: '70px',
                  backgroundColor: result.action === 'buy' ? '#dcfce7' : result.action === 'sell' ? '#fee2e2' : '#fef3c7',
                  color: result.action === 'buy' ? '#166534' : result.action === 'sell' ? '#991b1b' : '#92400e',
                  border: `1px solid ${result.action === 'buy' ? '#22c55e' : result.action === 'sell' ? '#ef4444' : '#f59e0b'}`
                }}>
                  {result.action.toUpperCase()}
                </div>
              )}
            </div>

            {/* ВЫХОД МОДЕЛИ (опционально) */}
            <div style={{ marginTop: '15px', fontSize: '13px', color: '#666' }}>
              <strong>Model output:</strong> {result.model_output?.toFixed(6)}
            </div>

            {/* РЕЗУЛЬТАТ ВЕРИФИКАЦИИ */}
            {verified !== null && (
              <div style={{ 
                marginTop: '20px', 
                padding: '12px',
                borderRadius: '6px', 
                textAlign: 'center',
                fontSize: '16px',
                fontWeight: 'bold',
                backgroundColor: verified ? '#dcfce7' : '#fee2e2',
                color: verified ? '#166534' : '#991b1b',
                border: `1px solid ${verified ? '#22c55e' : '#ef4444'}`
              }}>
                {verified ? '✅ PROOF VALID' : '❌ PROOF INVALID'}
              </div>
            )}
          </div>
        </div>
      ) : (
            <div style={{ textAlign: 'center', marginTop: '100px', color: '#94a3b8' }}>
              {loading ? 'Worker is processing your task. Please wait...' : 'Select a task or generate a new one'}
            </div>
          )}
        </div>
      </div>

     {/* ПРАВАЯ ПАНЕЛЬ: ИСТОРИЯ */}
      <div style={{ 
        width: '300px', 
        backgroundColor: '#fff', 
        borderLeft: '1px solid #ddd', 
        overflowY: 'auto', 
        height: '100vh'
      }}>
        <div style={{ 
          padding: '20px', 
          borderBottom: '1px solid #eee', 
          fontWeight: 'bold',
          position: 'sticky',
          top: 0,
          backgroundColor: '#fff',
          zIndex: 1
        }}>
          TASK HISTORY
        </div>
        {history.map(t => (
          <div 
            key={t.task_id} 
            onClick={() => selectTask(t)}
            style={{ 
              padding: '15px', 
              borderBottom: '1px solid #f0f0f0', 
              cursor: 'pointer', 
              backgroundColor: taskId === t.task_id ? '#eff6ff' : 'transparent'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', fontFamily: 'monospace', color: '#666' }}>{t.task_id.slice(0, 8)}...</div>
              <button 
                onClick={async (e) => {
                  e.stopPropagation();
                  if (confirm('Удалить задачу?')) {
                    await axios.delete(`${API}/tasks/${t.task_id}`);
                    fetchHistory();
                    if (taskId === t.task_id) {
                      setTaskId(null);
                      setResult(null);
                      setVerified(null);
                    }
                  }
                }}
                style={{ 
                  background: 'transparent', 
                  border: 'none', 
                  cursor: 'pointer', 
                  fontSize: '10px',
                  color: '#dc2626',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontWeight: 'normal'
                }}
              >
                Удалить
              </button>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '5px' }}>
              <span style={{ 
                fontSize: '10px', 
                padding: '2px 6px', 
                borderRadius: '4px', 
                backgroundColor: t.status === 'completed' ? '#dcfce7' : '#fef3c7',
                color: t.status === 'completed' ? '#166534' : '#92400e'
              }}>
                {t.status.toUpperCase()}
              </span>
              <span style={{ fontSize: '10px', color: '#999' }}>
                {t.completed_at ? new Date(t.completed_at).toLocaleTimeString() : '---'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;