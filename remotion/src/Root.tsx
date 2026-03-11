import React from 'react';
import { Composition } from 'remotion';
import { StockShort } from './StockShort';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="StockShort"
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      component={StockShort as any}
      durationInFrames={1350}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        symbol: 'AAPL',
        price: 150.0,
        changePct: 2.5,
        direction: 'rising',
        cardTitle: 'AAPL 2.5% 급등',
        cardSubtitle: '아이폰 판매 호조',
        script: '오늘 애플이 2.5퍼센트 급등했습니다. RSI는 55로 중립 구간이며, MACD는 골든크로스를 보이고 있습니다.',
        audioPath: '',
        rsi: 55,
        macd: 0.5,
        macdSignal: 0.3,
        volumeRatio: 1.8,
        bbPosition: 'upper',
        emaTrend: 'bullish',
        quantSummary: 'RSI 55(중립), MACD 골든크로스, 볼린저 상단, EMA 상승',
        chartData: [148, 149, 147, 150, 152, 151, 153, 150, 148, 150, 152, 154, 153, 155, 154, 156, 155, 157, 156, 158],
        companyNameKo: '애플',
        newsHeadlines: ['아이폰 16 판매 호조로 실적 기대감 상승', '워런 버핏 애플 지분 추가 매수 소식'],
      }}
    />
  );
};
