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

  testWidgets('Irregular offset plans fit and default to one floor', (tester) async {
    final rooms = [
      RoomLayout(roomId: 'hall', roomType: 'hallway', floor: 1, x: -10, y: 5,
        width: 4, length: 20, doors: [], windows: [],
        entrance: Opening(wall: 'south', offset: 0.5, width: 3)),
      RoomLayout(roomId: 'bed', roomType: 'bedroom_1', floor: 1, x: -6, y: 15,
        width: 12, length: 10, doors: [], windows: []),
      RoomLayout(roomId: 'stair', roomType: 'staircase', floor: 2, x: -10, y: 5,
        width: 6, length: 10, doors: [], windows: []),
    ];
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: FloorPlanViewer(rooms: rooms))));
    var paint = tester.widget<CustomPaint>(find.byWidgetPredicate((w) => w is CustomPaint && w.painter is FloorPlanPainter));
    var painter = paint.painter! as FloorPlanPainter;
    expect(painter.rooms.length, 2);
    expect(painter.minX, -10);
    expect(painter.maxY, 25);
    expect(painter.scale.isFinite && painter.scale > 0, isTrue);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: FloorPlanViewer(rooms: rooms, floorFilter: 2))));
    paint = tester.widget<CustomPaint>(find.byWidgetPredicate((w) => w is CustomPaint && w.painter is FloorPlanPainter));
    painter = paint.painter! as FloorPlanPainter;
    expect(painter.rooms.single.roomType, 'staircase');
    expect(tester.takeException(), isNull);
  });
}
