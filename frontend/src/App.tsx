import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Overview } from './pages/Overview';
import { Projects } from './pages/Projects';
import { DiscoverPapers } from './pages/DiscoverPapers';
import { PdfLibrary } from './pages/PdfLibrary';
import { PaperAnalysis } from './pages/PaperAnalysis';
import { ComparativeAnalysis } from './pages/ComparativeAnalysis';
import { KnowledgeGraph } from './pages/KnowledgeGraph';
import { ResearchGaps } from './pages/ResearchGaps';
import { ContradictionAnalysis } from './pages/ContradictionAnalysis';
import { EvidenceVerification } from './pages/EvidenceVerification';
import { ResearchReports } from './pages/ResearchReports';
import { Settings } from './pages/Settings';
import { Document, SystemHealth, ResearchProjectItem } from './types';
import { api } from './services/api';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [activePaperId, setActivePaperId] = useState<string | undefined>(undefined);
  const [projects, setProjects] = useState<ResearchProjectItem[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchData = async () => {
    setIsRefreshing(true);
    try {
      const [projList, docList, sysHealth] = await Promise.allSettled([
        api.getProjects(),
        api.getDocuments(selectedProjectId || undefined),
        api.getHealth(),
      ]);

      if (projList.status === 'fulfilled') {
        setProjects(projList.value);
      }
      if (docList.status === 'fulfilled') {
        setDocuments(docList.value);
      }
      if (sysHealth.status === 'fulfilled') {
        setHealth(sysHealth.value);
      }
    } catch (e) {
      console.error('Data refresh error', e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 20000);
    return () => clearInterval(interval);
  }, [selectedProjectId]);

  const handleNavigate = (tab: string, contextId?: string) => {
    setCurrentTab(tab);
    if (contextId) {
      setActivePaperId(contextId);
    }
  };

  const getPageHeaderInfo = () => {
    switch (currentTab) {
      case 'overview':
        return {
          title: 'Platform Overview & Literature Insights',
          subtitle: 'High-level synthesis metrics, active project telemetry, and recent paper ingestion.'
        };
      case 'projects':
        return {
          title: 'Research Projects & Workspaces',
          subtitle: 'Organize literature, analyses, gaps, and contradictions into dedicated domains.'
        };
      case 'discover':
        return {
          title: 'Academic Paper Discovery Agent',
          subtitle: 'Search arXiv, OpenAlex, and Semantic Scholar with strict factual provenance.'
        };
      case 'library':
        return {
          title: 'PDF Document Library & Ingestion',
          subtitle: 'Section-aware PDF parsing, chunking, and SQLite persistent indexing.'
        };
      case 'analysis':
        return {
          title: 'Single-Paper 14-Dimension Analysis',
          subtitle: 'Structured scientific report cards with exact page citations and reproducibility grading.'
        };
      case 'comparison':
        return {
          title: 'Cross-Paper Comparative Analysis',
          subtitle: '13-criteria comparative matrix, methodology divergence, and benchmark evaluation.'
        };
      case 'graph':
        return {
          title: 'Research Knowledge Graph Agent',
          subtitle: 'Relational NetworkX graph connecting algorithms, datasets, problems, and papers.'
        };
      case 'gaps':
        return {
          title: 'Research Gap Discovery Agent',
          subtitle: 'Author-stated limitations and cross-paper inferred gaps across 10 academic categories.'
        };
      case 'contradictions':
        return {
          title: 'Contradiction & Divergence Detection',
          subtitle: 'Genuine contradictions vs condition-dependent differences with side-by-side excerpts.'
        };
      case 'verification':
        return {
          title: 'Independent Evidence Verification Agent',
          subtitle: 'Validate factual claims and metrics against verbatim PDF passages with page provenance.'
        };
      case 'reports':
        return {
          title: 'Research Report Generator & Literature Dossiers',
          subtitle: 'Multi-format academic reports (PDF, Word, Markdown) with IEEE & APA citations and evidence grounding.'
        };
      case 'settings':
        return {
          title: 'Settings & Hardware Telemetry',
          subtitle: 'Windows 11 resource allocation, 8 GB RAM cap monitor, and local Ollama inference.'
        };
      default:
        return {
          title: 'Literature Intelligence Platform',
          subtitle: 'Academic SaaS Workspace'
        };
    }
  };

  const { title, subtitle } = getPageHeaderInfo();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-gray-900 font-sans">
      {/* Sidebar Navigation - Fixed 12 Items */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={(id) => setSelectedProjectId(id)}
        ramPercent={health?.ram_percent}
        ollamaConnected={health?.ollama_connected}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-white">
        <Header
          title={title}
          subtitle={subtitle}
          health={health}
          onRefresh={fetchData}
          isRefreshing={isRefreshing}
        />

        <main className="flex-1 overflow-y-auto p-6 bg-white">
          <div className="max-w-7xl mx-auto">
            {currentTab === 'overview' && (
              <Overview
                documents={documents}
                health={health}
                projects={projects}
                onNavigate={handleNavigate}
              />
            )}
            {currentTab === 'projects' && (
              <Projects
                projects={projects}
                selectedProjectId={selectedProjectId}
                onSelectActiveProject={(id) => setSelectedProjectId(id)}
                onNavigate={handleNavigate}
              />
            )}
            {currentTab === 'discover' && (
              <DiscoverPapers
                projects={projects}
                selectedProjectId={selectedProjectId}
                onPaperAdded={fetchData}
              />
            )}
            {currentTab === 'library' && (
              <PdfLibrary
                documents={documents}
                projects={projects}
                selectedProjectId={selectedProjectId}
                onRefresh={fetchData}
                onNavigate={handleNavigate}
              />
            )}
            {currentTab === 'analysis' && (
              <PaperAnalysis
                documents={documents}
                initialPaperId={activePaperId}
                onNavigate={handleNavigate}
              />
            )}
            {currentTab === 'comparison' && (
              <ComparativeAnalysis
                documents={documents}
              />
            )}
            {currentTab === 'graph' && (
              <KnowledgeGraph />
            )}
            {currentTab === 'gaps' && (
              <ResearchGaps
                projects={projects}
                selectedProjectId={selectedProjectId}
              />
            )}
            {currentTab === 'contradictions' && (
              <ContradictionAnalysis
                documents={documents}
                projects={projects}
                selectedProjectId={selectedProjectId}
              />
            )}
            {currentTab === 'verification' && (
              <EvidenceVerification
                documents={documents}
                selectedProjectId={selectedProjectId}
              />
            )}
            {currentTab === 'reports' && (
              <ResearchReports
                documents={documents}
                selectedProjectId={selectedProjectId}
              />
            )}
            {currentTab === 'settings' && (
              <Settings
                health={health}
                documents={documents}
                onRefreshHealth={fetchData}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
