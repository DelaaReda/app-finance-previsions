import { registerTemplate } from './registry';
import { marketOverview } from './templates/marketOverview';
import { macroPulse } from './templates/macroPulse';

registerTemplate(marketOverview);
registerTemplate(macroPulse);

export {};
