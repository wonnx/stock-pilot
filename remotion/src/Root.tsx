import { Composition } from 'remotion';
import { StockShort } from './StockShort';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="StockShort"
      component={StockShort}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        symbol: 'AAPL',
        price: 150.0,
        changePct: 2.5,
        direction: '상승',
        cardTitle: '애플 급등',
        cardSubtitle: '아이폰 판매 호조',
        script: '오늘 애플 주가가 2.5% 상승했습니다.',
        audioPath: '',
      }}
    />
  );
};
