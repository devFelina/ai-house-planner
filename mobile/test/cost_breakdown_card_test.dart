import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/cost_summary.dart';
import 'package:mobile/widgets/cost_breakdown_card.dart';

Map<String, dynamic> _line(String head, String item, num rate, num amount, num share,
        {String category = 'material', String unit = 'per_sqft', num quantity = 814, String quantityUnit = 'sq ft'}) =>
    {
      'itemName': item,
      'costHead': head,
      'category': category,
      'unitCostLkr': rate,
      'unit': unit,
      'appliedQuantity': quantity,
      'quantityUnit': quantityUnit,
      'terrainMultiplier': 1.0,
      'amountLkr': amount,
      'sharePercent': share,
      'provider': 'Manual',
      'sourceReference': 'Initial contractor benchmark',
      'pricingUpdatedAt': '2026-09-24T09:20:03Z',
    };

final _costJson = <String, dynamic>{
  'materialCostLkr': 11151800.17,
  'labourCostLkr': 3903130.06,
  'totalCostLkr': 15054930.23,
  'budgetDeltaPercent': null,
  'formulaVersion': 'category-area-v1',
  'appliedAreaSqft': 814,
  'terrainType': 'flat',
  'estimatedAt': '2026-10-04T11:42:45Z',
  'breakdown': [
    _line('Finishing', 'Finishing Materials', 2500, 2035000.03, 13.52),
    _line('Foundation', 'Foundation Materials', 3000, 2442000.04, 16.22),
    _line('MEP', 'MEP Materials', 1200, 976800.01, 6.49),
    _line('Roofing', 'Roofing Materials', 2500, 2035000.03, 13.52),
    _line('Structural', 'Structural Materials', 4500, 3663000.06, 24.33),
    _line('Labour', 'Construction Labour', 0.35, 3903130.06, 25.92,
        category: 'labour', unit: 'factor', quantity: 11151800.17, quantityUnit: 'material cost'),
  ],
};

Future<void> _pump(WidgetTester tester, CostSummary? cost) => tester.pumpWidget(MaterialApp(
      home: Scaffold(body: SingleChildScrollView(child: CostBreakdownCard(cost: cost))),
    ));

void main() {
  testWidgets('shows only the total until the breakdown is opened', (tester) async {
    await _pump(tester, CostSummary.tryParse(_costJson));

    expect(find.text('LKR 15,054,930.23'), findsOneWidget);
    expect(find.text('Show breakdown'), findsOneWidget);
    expect(find.text('Finishing'), findsNothing);
    expect(find.text('LKR 11,151,800.17'), findsNothing);
  });

  testWidgets('Show breakdown reveals cost heads and Hide breakdown collapses them', (tester) async {
    await _pump(tester, CostSummary.tryParse(_costJson));

    await tester.tap(find.byKey(const Key('cost-breakdown-toggle')));
    await tester.pumpAndSettle();

    expect(find.text('Hide breakdown'), findsOneWidget);
    expect(find.text('LKR 11,151,800.17'), findsOneWidget);
    expect(find.text('LKR 3,903,130.06'), findsNWidgets(2)); // labour tile and labour line
    for (final head in ['Finishing', 'Foundation', 'MEP', 'Roofing', 'Structural', 'Labour']) {
      expect(find.text(head), findsOneWidget);
    }
    expect(find.text('LKR 2,500/sq ft × 814 sq ft'), findsNWidgets(2));
    expect(find.text('0.35 × material cost'), findsOneWidget);
    expect(find.text('24.33%'), findsOneWidget);
    expect(find.text('Total estimated cost'), findsOneWidget);
    expect(find.text('Method: category-area-v1'), findsOneWidget);
    expect(find.text('Terrain: Flat'), findsOneWidget);

    await tester.tap(find.byKey(const Key('cost-breakdown-toggle')));
    await tester.pumpAndSettle();

    expect(find.text('Show breakdown'), findsOneWidget);
    expect(find.text('Finishing'), findsNothing);
  });

  testWidgets('missing estimate shows a not-available message without a toggle', (tester) async {
    await _pump(tester, CostSummary.tryParse(null));

    expect(find.text('Cost estimate is not available yet.'), findsOneWidget);
    expect(find.byKey(const Key('cost-breakdown-toggle')), findsNothing);
  });

  test('parses numbers sent as integers or strings and skips invalid lines', () {
    final cost = CostSummary.tryParse({
      'materialCostLkr': '1000',
      'labourCostLkr': 350,
      'totalCostLkr': '1350.5',
      'breakdown': [
        {'costHead': 'MEP', 'amountLkr': 1000},
        {'costHead': 'Broken'},
        'not a line',
      ],
    })!;

    expect(cost.totalCostLkr, 1350.5);
    expect(cost.labourCostLkr, 350);
    expect(cost.breakdown.single.costHead, 'MEP');
    expect(CostSummary.tryParse({'materialCostLkr': 1}), isNull);
  });

  test('formats LKR amounts like the web cost card', () {
    expect(formatLkr(15054930.23), 'LKR 15,054,930.23');
    expect(formatLkr(2500), 'LKR 2,500');
    expect(formatLkr(976800.01), 'LKR 976,800.01');
    expect(formatNumber(0.35), '0.35');
    expect(formatNumber(1.1), '1.1');
  });
}
