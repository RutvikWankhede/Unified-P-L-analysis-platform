export function showSkeleton(containerEl, variant) {
 if (!containerEl) return;
 
 let html = '';
 switch (variant) {
 case 'kpi':
 html = `
 <div class="skeleton" style="height: 24px; width: 60%; margin-bottom: 16px;"></div>
 <div class="skeleton" style="height: 40px; width: 80%; margin-bottom: 8px;"></div>
 <div class="skeleton" style="height: 16px; width: 40%;"></div>
 `;
 break;
 case 'chart':
 html = `
 <div class="skeleton" style="height: 100%; width: 100%; min-height: 200px;"></div>
 `;
 break;
 case 'list':
 html = `
 <div class="skeleton" style="height: 48px; width: 100%; margin-bottom: 8px;"></div>
 <div class="skeleton" style="height: 48px; width: 100%; margin-bottom: 8px;"></div>
 <div class="skeleton" style="height: 48px; width: 100%;"></div>
 `;
 break;
 case 'table':
 html = `
 <div class="skeleton" style="height: 32px; width: 100%; margin-bottom: 16px;"></div>
 <div class="skeleton" style="height: 40px; width: 100%; margin-bottom: 8px;"></div>
 <div class="skeleton" style="height: 40px; width: 100%; margin-bottom: 8px;"></div>
 <div class="skeleton" style="height: 40px; width: 100%;"></div>
 `;
 break;
 case 'text-3-line':
 html = `
 <div class="skeleton" style="height: 16px; width: 90%; margin-bottom: 8px;"></div>
 <div class="skeleton" style="height: 16px; width: 85%; margin-bottom: 8px;"></div>
 <div class="skeleton" style="height: 16px; width: 70%;"></div>
 `;
 break;
 default:
 html = '<div class="skeleton" style="height: 100%; width: 100%;"></div>';
 }
 
 containerEl.innerHTML = html;
 containerEl.setAttribute('data-skeleton-active', 'true');
}

export function hideSkeleton(containerEl) {
 if (!containerEl) return;
 containerEl.removeAttribute('data-skeleton-active');
 containerEl.innerHTML = '';
}
