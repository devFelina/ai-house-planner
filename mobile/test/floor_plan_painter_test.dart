import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/widgets/floor_plan_painter.dart';

void main() {
  testWidgets('FloorPlanViewer renders correctly', (WidgetTester tester) async {
    final testRooms = [
      RoomLayout(
        roomId: '1',
        roomType: 'living_room',
        floor: 1,
        x: 0,
        y: 0,
        width: 10,
        length: 10,
        doors: [],
        windows: []
      )
    ];

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: FloorPlanViewer(rooms: testRooms),
      ),
    ));

    expect(find.byType(CustomPaint), findsOneWidget);
    // The painter should be drawing the layout, we can just verify it doesn't crash
  });

  testWidgets('FloorPlanViewer shows no rooms message when empty', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: FloorPlanViewer(rooms: []),
      ),
    ));

    expect(find.text('No rooms to display for this floor.'), findsOneWidget);
  });
}
