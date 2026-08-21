import { api } from './api.js';
import './auth.js';

document.addEventListener('DOMContentLoaded', initWorkflow);
window.initWorkflow = initWorkflow;

let bpmnViewer = null;

const bpmnXML = \<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
 <bpmn:process id="Process_1" isExecutable="true">
 <bpmn:startEvent id="StartEvent_1" name="Upload Received">
 <bpmn:outgoing>Flow_1</bpmn:outgoing>
 </bpmn:startEvent>
 <bpmn:serviceTask id="Task_Validate" name="Validate Data">
 <bpmn:incoming>Flow_1</bpmn:incoming>
 <bpmn:outgoing>Flow_2</bpmn:outgoing>
 </bpmn:serviceTask>
 <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_Validate" />
 <bpmn:userTask id="Task_Map" name="Schema Mapping">
 <bpmn:incoming>Flow_2</bpmn:incoming>
 <bpmn:outgoing>Flow_3</bpmn:outgoing>
 </bpmn:userTask>
 <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_Validate" targetRef="Task_Map" />
 <bpmn:serviceTask id="Task_Ingest" name="Ingest to DB">
 <bpmn:incoming>Flow_3</bpmn:incoming>
 <bpmn:outgoing>Flow_4</bpmn:outgoing>
 </bpmn:serviceTask>
 <bpmn:sequenceFlow id="Flow_3" sourceRef="Task_Map" targetRef="Task_Ingest" />
 <bpmn:endEvent id="EndEvent_1" name="Success">
 <bpmn:incoming>Flow_4</bpmn:incoming>
 </bpmn:endEvent>
 <bpmn:sequenceFlow id="Flow_4" sourceRef="Task_Ingest" targetRef="EndEvent_1" />
 </bpmn:process>
 <bpmndi:BPMNDiagram id="BPMNDiagram_1">
 <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
 <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
 <dc:Bounds x="150" y="100" width="36" height="36" />
 </bpmndi:BPMNShape>
 <bpmndi:BPMNShape id="Task_Validate_di" bpmnElement="Task_Validate">
 <dc:Bounds x="240" y="78" width="100" height="80" />
 </bpmndi:BPMNShape>
 <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
 <di:waypoint x="186" y="118" />
 <di:waypoint x="240" y="118" />
 </bpmndi:BPMNEdge>
 <bpmndi:BPMNShape id="Task_Map_di" bpmnElement="Task_Map">
 <dc:Bounds x="400" y="78" width="100" height="80" />
 </bpmndi:BPMNShape>
 <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
 <di:waypoint x="340" y="118" />
 <di:waypoint x="400" y="118" />
 </bpmndi:BPMNEdge>
 <bpmndi:BPMNShape id="Task_Ingest_di" bpmnElement="Task_Ingest">
 <dc:Bounds x="560" y="78" width="100" height="80" />
 </bpmndi:BPMNShape>
 <bpmndi:BPMNEdge id="Flow_3_di" bpmnElement="Flow_3">
 <di:waypoint x="500" y="118" />
 <di:waypoint x="560" y="118" />
 </bpmndi:BPMNEdge>
 <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">
 <dc:Bounds x="720" y="100" width="36" height="36" />
 </bpmndi:BPMNShape>
 <bpmndi:BPMNEdge id="Flow_4_di" bpmnElement="Flow_4">
 <di:waypoint x="660" y="118" />
 <di:waypoint x="720" y="118" />
 </bpmndi:BPMNEdge>
 </bpmndi:BPMNPlane>
 </bpmndi:BPMNDiagram>
</bpmn:definitions>\;

async function initWorkflow() {
 try {
 const data = await api.get(api.endpoints.workflows).catch(() => ({}));
 
 // Fallback mock stats if missing
 document.getElementById('stat-running').textContent = data.running || 4;
 document.getElementById('stat-completed').textContent = data.completed || 128;
 document.getElementById('stat-failed').textContent = data.failed || 2;
 document.getElementById('stat-tasks').textContent = data.user_tasks || 5;

 renderExecutionHistory(data.executions || []);
 
 // Init BPMN Viewer if not initialized
 if (!bpmnViewer && window.BpmnJS) {
 bpmnViewer = new window.BpmnJS({ container: '#canvas' });
 await bpmnViewer.importXML(bpmnXML);
 const canvas = bpmnViewer.get('canvas');
 canvas.zoom('fit-viewport');
 
 const eventBus = bpmnViewer.get('eventBus');
 eventBus.on('element.click', (e) => {
 showNodeDetails(e.element);
 });
 
 // Highlight current active node
 const overlays = bpmnViewer.get('overlays');
 const registry = bpmnViewer.get('elementRegistry');
 const activeNode = registry.get('Task_Map'); // Example
 if(activeNode) {
 bpmnViewer.get('canvas').addMarker('Task_Map', 'highlight-node');
 // Add pulse animation class to the SVG group manually since bpmn.js overlays might not support complex tailwind animations natively on the svg path
 const svgG = document.querySelector('[data-element-id="Task_Map"] .djs-visual');
 if(svgG) svgG.classList.add('animate-pulse');
 }
 }
 } catch(err) {
 console.error("Workflow initialization failed", err);
 }
}

function renderExecutionHistory(executions) {
 const tbody = document.getElementById('execution-tbody');
 if(!executions || executions.length === 0) {
 //  executions for demo
 executions = [
 { id: 'cam-782a1', key: 'UP-dataset-102', start: '2 mins ago', status: 'Running' },
 { id: 'cam-782a0', key: 'UP-dataset-101', start: '1 hour ago', status: 'Completed' },
 { id: 'cam-78299', key: 'UP-dataset-100', start: '2 hours ago', status: 'Failed' }
 ];
 }
 
 tbody.innerHTML = executions.map(ex => {
 let statusClass = 'bg-blue-100 text-blue-700';
 if(ex.status === 'Completed') statusClass = 'bg-green-100 text-green-700';
 if(ex.status === 'Failed') statusClass = 'bg-red-100 text-red-700';
 
 return `
 <tr class="hover:bg-slate-50 transition">
 <td class="px-6 py-4 font-mono text-slate-600 ">${ex.id}</td>
 <td class="px-6 py-4 font-semibold text-slate-900 ">${ex.key}</td>
 <td class="px-6 py-4 text-slate-500 ">${ex.start}</td>
 <td class="px-6 py-4">
 <span class="px-2 py-1 text-[10px] font-bold uppercase rounded ${statusClass}">${ex.status}</span>
 </td>
 <td class="px-6 py-4 flex gap-2">
 <button class="text-primary hover:underline text-xs font-semibold">Details</button>
 ${ex.status === 'Running' ? `<button class="text-red-500 hover:underline text-xs font-semibold" onclick="window.showToast('Execution cancelled', 'success')">Cancel</button>` : ''}
 ${ex.status === 'Failed' ? `<button class="text-orange-500 hover:underline text-xs font-semibold" onclick="window.showToast('Execution restarted', 'success')">Retry</button>` : ''}
 </td>
 </tr>
 `;
 }).join('');
}

function showNodeDetails(element) {
 const panel = document.getElementById('node-details');
 if(!element || element.type === 'bpmn:Process') {
 panel.innerHTML = '<p class="text-sm text-slate-500">Click any BPMN node on the left to view its variables, execution history, and status.</p>';
 return;
 }
 
 const nodeName = element.businessObject.name || element.id;
 
 panel.innerHTML = \
 <h4 class="font-bold text-slate-900 mb-2">\</h4>
 <div class="space-y-4">
 <div class="bg-slate-50 p-3 rounded border border-slate-100 ">
 <p class="text-xs text-slate-500 mb-1">Status</p>
 <p class="text-sm font-semibold \">\</p>
 </div>
 <div class="bg-slate-50 p-3 rounded border border-slate-100 ">
 <p class="text-xs text-slate-500 mb-1">Execution Time</p>
 <p class="text-sm font-semibold text-slate-700 ">12ms</p>
 </div>
 <div class="bg-slate-50 p-3 rounded border border-slate-100 ">
 <p class="text-xs text-slate-500 mb-1">Variables</p>
 <pre class="text-xs text-slate-600 mt-1 font-mono break-all">{
 "file_id": "req-9a3b",
 "status": "VALIDATED",
 "rows": 4350
}</pre>
 </div>
 <div class="bg-red-50 p-3 rounded border border-red-100 ">
 <p class="text-xs font-bold text-red-700 mb-1 flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">warning</span> Incident Panel</p>
 <p class="text-xs text-red-600 ">No active incidents.</p>
 </div>
 </div>
 \;
}
