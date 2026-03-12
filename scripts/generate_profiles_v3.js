const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const OUTPUT_DIR = '/Users/jwkim/stock-pilot/output/profiles_v3';

const designs = [
  // 1. 그라데이션 배경 — 동적 캔들차트 그라데이션
  {
    name: 'profile_v3_01_gradient',
    html: `
      <div style="width:640px;height:640px;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:'Arial',sans-serif;overflow:hidden;position:relative;">
        <svg style="position:absolute;top:0;left:0;width:640px;height:640px;opacity:0.15" viewBox="0 0 640 640">
          ${Array.from({length:12},(_,i)=>{const x=30+i*52,h=80+Math.sin(i)*120+Math.cos(i*1.3)*80,y=320-h/2;return `<rect x="${x}" y="${y}" width="28" height="${h}" fill="${i%3===0?'#ff6b6b':i%3===1?'#4ecdc4':'#ffe66d'}" rx="4"/>`;}).join('')}
        </svg>
        <div style="font-size:88px;font-weight:900;color:white;letter-spacing:-4px;text-shadow:0 0 40px rgba(255,255,255,0.5);">S<span style="color:#4ecdc4;">S</span></div>
        <div style="font-size:16px;color:rgba(255,255,255,0.7);letter-spacing:8px;margin-top:8px;text-transform:uppercase;">Stock Snap</div>
        <div style="position:absolute;bottom:32px;left:50%;transform:translateX(-50%);width:120px;height:3px;background:linear-gradient(90deg,#4ecdc4,#556fff);border-radius:2px;"></div>
      </div>
    `
  },
  // 2. 일러스트 스타일 — 손그림 느낌 주식 캐릭터
  {
    name: 'profile_v3_02_illustration',
    html: `
      <div style="width:640px;height:640px;background:#fef9ef;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:'Georgia',serif;overflow:hidden;position:relative;">
        <svg viewBox="0 0 640 640" width="640" height="640" style="position:absolute;top:0;left:0;">
          <!-- 배경 원 -->
          <circle cx="320" cy="320" r="260" fill="#fff3d4" stroke="#f4a62a" stroke-width="3" stroke-dasharray="12,6"/>
          <!-- 작은 별들 -->
          ${Array.from({length:8},(_,i)=>{const angle=i*45*Math.PI/180,r=200,x=320+r*Math.cos(angle),y=320+r*Math.sin(angle);return `<polygon points="${x},${y-10} ${x+4},${y-2} ${x+12},${y-2} ${x+6},${y+4} ${x+8},${y+12} ${x},${y+8} ${x-8},${y+12} ${x-6},${y+4} ${x-12},${y-2} ${x-4},${y-2}" fill="#f4a62a" opacity="0.5"/>`;}).join('')}
          <!-- 캐릭터 몸 -->
          <circle cx="320" cy="290" r="75" fill="#ffd89b" stroke="#e8a000" stroke-width="3"/>
          <!-- 눈 -->
          <circle cx="298" cy="278" r="9" fill="#2d3436"/>
          <circle cx="342" cy="278" r="9" fill="#2d3436"/>
          <circle cx="302" cy="274" r="3" fill="white"/>
          <circle cx="346" cy="274" r="3" fill="white"/>
          <!-- 웃음 -->
          <path d="M298 305 Q320 325 342 305" stroke="#2d3436" stroke-width="4" fill="none" stroke-linecap="round"/>
          <!-- 모자 -->
          <rect x="262" y="218" width="116" height="18" rx="5" fill="#2d3436"/>
          <rect x="282" y="188" width="76" height="34" rx="8" fill="#2d3436"/>
          <!-- 주식 그래프 미니 -->
          <polyline points="278,348 295,332 312,340 332,318 352,325 370,308" stroke="#f4a62a" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <!-- 타이틀 -->
          <text x="320" y="442" text-anchor="middle" font-size="24" font-family="Georgia" font-weight="bold" fill="#2d3436">Stock.snap</text>
          <text x="320" y="470" text-anchor="middle" font-size="14" font-family="Georgia" fill="#888">주식 뉴스 큐레이터</text>
        </svg>
      </div>
    `
  },
  // 3. 타이포그래피 중심 — 대형 텍스트 레이아웃
  {
    name: 'profile_v3_03_typography',
    html: `
      <div style="width:640px;height:640px;background:#1a1a1a;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;padding:60px;font-family:'Arial Black',sans-serif;overflow:hidden;position:relative;">
        <div style="font-size:13px;color:#ff6b35;letter-spacing:6px;text-transform:uppercase;margin-bottom:20px;">DAILY STOCK NEWS</div>
        <div style="font-size:110px;font-weight:900;color:white;line-height:0.9;margin-bottom:16px;">
          <span style="color:#ff6b35;">S</span>TOCK
        </div>
        <div style="font-size:110px;font-weight:900;color:white;line-height:0.9;margin-bottom:24px;">
          <span style="color:white;">SN</span><span style="color:#ff6b35;">AP</span>
        </div>
        <div style="width:80px;height:5px;background:#ff6b35;margin-bottom:24px;"></div>
        <div style="font-size:16px;color:#888;letter-spacing:3px;">@stock.snap</div>
        <!-- 배경 텍스처 숫자들 -->
        <div style="position:absolute;right:-20px;top:40px;font-size:200px;font-weight:900;color:rgba(255,255,255,0.03);line-height:1;">₩</div>
        <div style="position:absolute;right:60px;bottom:60px;font-size:80px;font-weight:900;color:rgba(255,107,53,0.08);">▲</div>
      </div>
    `
  },
  // 4. 미니멀 아이콘 — 순수 기하학
  {
    name: 'profile_v3_04_minimal',
    html: `
      <div style="width:640px;height:640px;background:#f8f8f8;display:flex;align-items:center;justify-content:center;overflow:hidden;">
        <svg viewBox="0 0 640 640" width="640" height="640">
          <!-- 외부 원 -->
          <circle cx="320" cy="320" r="220" fill="none" stroke="#1a1a1a" stroke-width="2"/>
          <!-- 내부 사각형 다이아몬드 -->
          <rect x="220" y="220" width="200" height="200" fill="none" stroke="#1a1a1a" stroke-width="2" transform="rotate(45 320 320)"/>
          <!-- 중앙 선 차트 -->
          <polyline points="230,350 265,300 300,320 335,265 370,280 410,240" stroke="#1a1a1a" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <!-- 상승 화살표 -->
          <line x1="410" y1="240" x2="425" y2="220" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
          <line x1="415" y1="238" x2="425" y2="220" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
          <!-- 하단 텍스트 -->
          <text x="320" y="490" text-anchor="middle" font-size="18" font-family="Arial" letter-spacing="10" fill="#1a1a1a">STOCK.SNAP</text>
        </svg>
      </div>
    `
  },
  // 5. 패턴/텍스처 — 주식 티커 반복 패턴
  {
    name: 'profile_v3_05_pattern',
    html: `
      <div style="width:640px;height:640px;background:#0d1117;overflow:hidden;position:relative;display:flex;align-items:center;justify-content:center;">
        <!-- 배경 텍스트 패턴 -->
        <div style="position:absolute;top:0;left:0;width:640px;height:640px;overflow:hidden;opacity:0.12;font-family:monospace;font-size:11px;color:#00ff88;line-height:1.8;word-break:break-all;padding:10px;">
          $AAPL+2.3% $TSLA-1.2% $NVDA+4.1% $AMZN+0.8% $MSFT+1.5% $GOOGL+0.3% $META+2.7% $NFLX-0.5% $BNTX+3.2% $AMD+1.9% $INTC-2.1% $ORCL+0.6% $CRM+1.1% $ADBE+2.4% $PYPL-1.8% $SQ+3.5% $SHOP+2.1% $ROKU-0.9% $SNAP+4.2% $TWTR+1.7% $UBER+0.4% $LYFT-2.3% $ABNB+5.1% $DASH+2.8% $RBLX+3.6% $COIN+6.2% $HOOD+1.4% $SOFI+2.9% $PLTR+4.7% $LCID-3.1% $RIVN+2.5% $NIO+1.8% $XPEV+3.2% $LI+2.4% $BABA-1.5% $JD+0.7% $PDD+2.1% $BIDU+1.3% $TCEHY+0.9% $NTES+1.2%
          $AAPL+2.3% $TSLA-1.2% $NVDA+4.1% $AMZN+0.8% $MSFT+1.5% $GOOGL+0.3% $META+2.7% $NFLX-0.5% $BNTX+3.2% $AMD+1.9%
          $INTC-2.1% $ORCL+0.6% $CRM+1.1% $ADBE+2.4% $PYPL-1.8% $SQ+3.5% $SHOP+2.1% $ROKU-0.9% $SNAP+4.2% $TWTR+1.7%
        </div>
        <!-- 중앙 로고 -->
        <div style="position:relative;background:#0d1117;padding:20px 32px;border:1px solid #00ff88;box-shadow:0 0 30px rgba(0,255,136,0.2);">
          <div style="font-family:monospace;font-size:48px;font-weight:900;color:#00ff88;letter-spacing:4px;">S.SNAP</div>
          <div style="font-family:monospace;font-size:11px;color:#00ff88;opacity:0.6;text-align:center;letter-spacing:6px;margin-top:4px;">MARKET FEED</div>
        </div>
      </div>
    `
  },
  // 6. 사진 느낌 (추상적) — 블러/빛 효과
  {
    name: 'profile_v3_06_abstract_photo',
    html: `
      <div style="width:640px;height:640px;overflow:hidden;position:relative;background:#050510;">
        <svg style="position:absolute;top:0;left:0;" width="640" height="640" viewBox="0 0 640 640">
          <defs>
            <radialGradient id="b1" cx="30%" cy="30%">
              <stop offset="0%" stop-color="#6c63ff" stop-opacity="0.9"/>
              <stop offset="100%" stop-color="#6c63ff" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="b2" cx="70%" cy="60%">
              <stop offset="0%" stop-color="#ff6584" stop-opacity="0.8"/>
              <stop offset="100%" stop-color="#ff6584" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="b3" cx="50%" cy="80%">
              <stop offset="0%" stop-color="#43e97b" stop-opacity="0.7"/>
              <stop offset="100%" stop-color="#43e97b" stop-opacity="0"/>
            </radialGradient>
            <filter id="blur1">
              <feGaussianBlur stdDeviation="40"/>
            </filter>
          </defs>
          <rect width="640" height="640" fill="url(#b1)" filter="url(#blur1)"/>
          <rect width="640" height="640" fill="url(#b2)" filter="url(#blur1)"/>
          <rect width="640" height="640" fill="url(#b3)" filter="url(#blur1)"/>
          <!-- 선 그래프 오버레이 -->
          <polyline points="80,500 160,380 240,420 320,280 400,310 480,200 560,230" stroke="rgba(255,255,255,0.3)" stroke-width="2" fill="none"/>
          <polyline points="80,520 160,440 240,460 320,340 400,360 480,260 560,290" stroke="rgba(255,255,255,0.1)" stroke-width="1" fill="none"/>
        </svg>
        <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;">
          <div style="font-size:72px;font-weight:100;color:white;letter-spacing:12px;font-family:'Arial',sans-serif;">SS</div>
          <div style="font-size:13px;color:rgba(255,255,255,0.6);letter-spacing:5px;margin-top:12px;font-family:'Arial',sans-serif;">STOCK · SNAP</div>
        </div>
      </div>
    `
  },
  // 7. 3D 느낌 — 아이소메트릭 주식 큐브
  {
    name: 'profile_v3_07_3d_isometric',
    html: `
      <div style="width:640px;height:640px;background:#f0f4f8;display:flex;align-items:center;justify-content:center;overflow:hidden;">
        <svg viewBox="0 0 640 640" width="640" height="640">
          <!-- 아이소메트릭 바 차트 큐브들 -->
          <!-- 큐브 1 (가장 큰) -->
          <g transform="translate(180, 200)">
            <!-- top face -->
            <polygon points="60,0 120,30 60,60 0,30" fill="#4CAF50"/>
            <!-- right face -->
            <polygon points="120,30 120,130 60,160 60,60" fill="#2E7D32"/>
            <!-- left face -->
            <polygon points="0,30 60,60 60,160 0,130" fill="#388E3C"/>
            <!-- label -->
            <text x="60" y="200" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#2E7D32">▲ 4.2%</text>
          </g>
          <!-- 큐브 2 -->
          <g transform="translate(300, 250)">
            <!-- top face -->
            <polygon points="50,0 100,25 50,50 0,25" fill="#2196F3"/>
            <!-- right face -->
            <polygon points="100,25 100,100 50,125 50,50" fill="#1565C0"/>
            <!-- left face -->
            <polygon points="0,25 50,50 50,125 0,100" fill="#1976D2"/>
            <text x="50" y="160" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#1976D2">▲ 2.8%</text>
          </g>
          <!-- 큐브 3 (빨간, 하락) -->
          <g transform="translate(410, 300)">
            <!-- top face -->
            <polygon points="40,0 80,20 40,40 0,20" fill="#ef5350"/>
            <!-- right face -->
            <polygon points="80,20 80,70 40,90 40,40" fill="#b71c1c"/>
            <!-- left face -->
            <polygon points="0,20 40,40 40,90 0,70" fill="#c62828"/>
            <text x="40" y="115" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold" fill="#c62828">▼ 1.1%</text>
          </g>
          <!-- 바닥 그리드 -->
          <line x1="120" y1="420" x2="520" y2="420" stroke="#ccc" stroke-width="1"/>
          <line x1="160" y1="400" x2="160" y2="425" stroke="#ccc" stroke-width="1"/>
          <line x1="240" y1="400" x2="240" y2="425" stroke="#ccc" stroke-width="1"/>
          <line x1="320" y1="400" x2="320" y2="425" stroke="#ccc" stroke-width="1"/>
          <!-- 타이틀 -->
          <text x="320" y="490" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold" fill="#1a1a1a">STOCK.SNAP</text>
          <text x="320" y="514" text-anchor="middle" font-family="Arial" font-size="13" fill="#888">MARKET INSIGHT</text>
        </svg>
      </div>
    `
  },
  // 8. 레트로/빈티지 — 80년대 신문 스타일
  {
    name: 'profile_v3_08_retro_vintage',
    html: `
      <div style="width:640px;height:640px;background:#f5e6c8;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:'Georgia',serif;position:relative;overflow:hidden;">
        <!-- 빈티지 테두리 -->
        <div style="position:absolute;inset:20px;border:3px solid #8b4513;pointer-events:none;"></div>
        <div style="position:absolute;inset:28px;border:1px solid #8b4513;pointer-events:none;"></div>
        <!-- 상단 장식 -->
        <div style="position:absolute;top:40px;left:50%;transform:translateX(-50%);display:flex;gap:16px;align-items:center;">
          <div style="width:60px;height:2px;background:#8b4513;"></div>
          <div style="font-size:18px;color:#8b4513;">★</div>
          <div style="width:60px;height:2px;background:#8b4513;"></div>
        </div>
        <!-- 신문 헤더 -->
        <div style="font-size:13px;letter-spacing:8px;color:#8b4513;margin-bottom:8px;text-transform:uppercase;">The</div>
        <div style="font-size:72px;font-weight:900;color:#2c1810;line-height:1;border-top:4px solid #2c1810;border-bottom:4px solid #2c1810;padding:8px 32px;margin-bottom:8px;">STOCK</div>
        <div style="font-size:32px;letter-spacing:16px;color:#8b4513;margin-bottom:24px;">SNAP</div>
        <!-- 구분선 -->
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px;">
          <div style="width:80px;height:1px;background:#8b4513;"></div>
          <div style="font-size:12px;color:#8b4513;letter-spacing:3px;">EST. 2024</div>
          <div style="width:80px;height:1px;background:#8b4513;"></div>
        </div>
        <!-- 서브 텍스트 -->
        <div style="font-size:13px;color:#5c4030;letter-spacing:5px;text-align:center;font-style:italic;">Daily Market Intelligence</div>
        <!-- 하단 장식 -->
        <div style="position:absolute;bottom:40px;left:50%;transform:translateX(-50%);display:flex;gap:16px;align-items:center;">
          <div style="width:60px;height:2px;background:#8b4513;"></div>
          <div style="font-size:18px;color:#8b4513;">★</div>
          <div style="width:60px;height:2px;background:#8b4513;"></div>
        </div>
        <!-- 배경 노이즈 텍스처 효과 -->
        <div style="position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(139,69,19,0.03) 3px,rgba(139,69,19,0.03) 4px);pointer-events:none;"></div>
      </div>
    `
  },
  // 9. 네온/사이버펑크 — 어두운 배경에 네온 글로우
  {
    name: 'profile_v3_09_neon_cyberpunk',
    html: `
      <div style="width:640px;height:640px;background:#080818;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:'Arial',sans-serif;overflow:hidden;position:relative;">
        <!-- 그리드 배경 -->
        <svg style="position:absolute;top:0;left:0;opacity:0.15" width="640" height="640" viewBox="0 0 640 640">
          ${Array.from({length:17},(_,i)=>`<line x1="${i*40}" y1="0" x2="${i*40}" y2="640" stroke="#00ffff" stroke-width="0.5"/>`).join('')}
          ${Array.from({length:17},(_,i)=>`<line x1="0" y1="${i*40}" x2="640" y2="${i*40}" stroke="#00ffff" stroke-width="0.5"/>`).join('')}
          <!-- 원근감 -->
          ${Array.from({length:9},(_,i)=>`<line x1="${320}" y1="${320}" x2="${i*80}" y2="640" stroke="#00ffff" stroke-width="0.3" opacity="0.5"/>`).join('')}
        </svg>
        <!-- 네온 텍스트 -->
        <div style="position:relative;text-align:center;">
          <div style="font-size:96px;font-weight:900;color:transparent;-webkit-text-stroke:2px #ff00ff;text-shadow:0 0 20px #ff00ff,0 0 40px #ff00ff,0 0 80px #ff00ff;letter-spacing:8px;">SS</div>
          <div style="font-size:20px;color:#00ffff;letter-spacing:12px;text-shadow:0 0 10px #00ffff,0 0 20px #00ffff;margin-top:-8px;">STOCK.SNAP</div>
        </div>
        <!-- 스캔라인 효과 -->
        <div style="position:absolute;bottom:80px;left:50%;transform:translateX(-50%);display:flex;gap:8px;">
          ${Array.from({length:5},(_,i)=>`<div style="width:${16+i*4}px;height:4px;background:#ff00ff;box-shadow:0 0 8px #ff00ff;opacity:${0.4+i*0.15};"></div>`).join('')}
          ${Array.from({length:4},(_,i)=>`<div style="width:${28-i*4}px;height:4px;background:#ff00ff;box-shadow:0 0 8px #ff00ff;opacity:${0.8-i*0.15};"></div>`).join('')}
        </div>
        <!-- 코너 장식 -->
        <div style="position:absolute;top:40px;left:40px;width:40px;height:40px;border-top:2px solid #00ffff;border-left:2px solid #00ffff;box-shadow:-4px -4px 12px rgba(0,255,255,0.3);"></div>
        <div style="position:absolute;top:40px;right:40px;width:40px;height:40px;border-top:2px solid #00ffff;border-right:2px solid #00ffff;box-shadow:4px -4px 12px rgba(0,255,255,0.3);"></div>
        <div style="position:absolute;bottom:40px;left:40px;width:40px;height:40px;border-bottom:2px solid #ff00ff;border-left:2px solid #ff00ff;box-shadow:-4px 4px 12px rgba(255,0,255,0.3);"></div>
        <div style="position:absolute;bottom:40px;right:40px;width:40px;height:40px;border-bottom:2px solid #ff00ff;border-right:2px solid #ff00ff;box-shadow:4px 4px 12px rgba(255,0,255,0.3);"></div>
      </div>
    `
  },
  // 10. 자연/오가닉 — 초록 잎사귀 + 유기적 형태
  {
    name: 'profile_v3_10_natural_organic',
    html: `
      <div style="width:640px;height:640px;background:#f0f7ee;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;">
        <svg viewBox="0 0 640 640" width="640" height="640">
          <defs>
            <radialGradient id="leafGrad" cx="30%" cy="30%">
              <stop offset="0%" stop-color="#a8e6a3"/>
              <stop offset="100%" stop-color="#2e7d32"/>
            </radialGradient>
          </defs>
          <!-- 유기적 블롭 배경 -->
          <ellipse cx="200" cy="200" rx="220" ry="180" fill="#c8e6c9" opacity="0.5" transform="rotate(-20 200 200)"/>
          <ellipse cx="450" cy="430" rx="200" ry="160" fill="#a5d6a7" opacity="0.4" transform="rotate(15 450 430)"/>
          <!-- 잎사귀 -->
          <path d="M320 160 Q420 200 400 320 Q380 400 320 440 Q260 400 240 320 Q220 200 320 160" fill="url(#leafGrad)" opacity="0.9"/>
          <path d="M320 160 L320 440" stroke="#1b5e20" stroke-width="2.5" stroke-dasharray="8,4" opacity="0.6"/>
          <!-- 잎맥 -->
          <path d="M320 220 Q360 250 380 290" stroke="#1b5e20" stroke-width="1.5" fill="none" opacity="0.5"/>
          <path d="M320 220 Q280 250 260 290" stroke="#1b5e20" stroke-width="1.5" fill="none" opacity="0.5"/>
          <path d="M320 290 Q355 310 370 345" stroke="#1b5e20" stroke-width="1.5" fill="none" opacity="0.5"/>
          <path d="M320 290 Q285 310 270 345" stroke="#1b5e20" stroke-width="1.5" fill="none" opacity="0.5"/>
          <!-- 작은 점들 -->
          <circle cx="160" cy="350" r="8" fill="#81c784" opacity="0.6"/>
          <circle cx="480" cy="200" r="6" fill="#66bb6a" opacity="0.5"/>
          <circle cx="500" cy="460" r="10" fill="#a5d6a7" opacity="0.5"/>
          <circle cx="140" cy="180" r="5" fill="#aed581" opacity="0.6"/>
          <!-- 텍스트 -->
          <text x="320" y="510" text-anchor="middle" font-family="Georgia" font-size="22" font-weight="bold" fill="#2e7d32">Stock.snap</text>
          <text x="320" y="538" text-anchor="middle" font-family="Georgia" font-size="14" font-style="italic" fill="#558b2f">grow your insights</text>
        </svg>
      </div>
    `
  }
];

async function generateProfiles() {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 640, height: 640 });

  for (const design of designs) {
    const html = `<!DOCTYPE html><html><body style="margin:0;padding:0;width:640px;height:640px;overflow:hidden;">${design.html}</body></html>`;
    await page.setContent(html, { waitUntil: 'domcontentloaded' });
    const outputPath = path.join(OUTPUT_DIR, `${design.name}.png`);
    await page.screenshot({ path: outputPath, clip: { x: 0, y: 0, width: 640, height: 640 } });
    console.log(`✅ Generated: ${design.name}.png`);
  }

  await browser.close();
  console.log('\n🎉 All 10 profile images generated!');
}

generateProfiles().catch(console.error);
