import 'dart:math';
import 'package:flutter/material.dart';

/// Data model for a single room opening (door or window).
class Opening {
  final String wall;
  final double offset;
  final double width;

  Opening({required this.wall, required this.offset, required this.width});

  factory Opening.fromJson(Map<String, dynamic> json) {
    return Opening(
      wall: json['wall'],
      offset: (json['offset'] as num).toDouble(),
      width: (json['width'] as num).toDouble(),
    );
  }
}

/// Data model for a single room in the floor plan.
class RoomLayout {
  final String roomId;
  final String roomType;
  final String? name;
  final int floor;
  final double x;
  final double y;
  final double width;
  final double length;
  final List<Opening> doors;
  final List<Opening> windows;

  RoomLayout({
    required this.roomId,
    required this.roomType,
    this.name,
    required this.floor,
    required this.x,
    required this.y,
    required this.width,
    required this.length,
    required this.doors,
    required this.windows,
  });

  factory RoomLayout.fromJson(Map<String, dynamic> json) {
    return RoomLayout(
      roomId: json['room_id'] ?? json['roomId'] ?? '',
      roomType: json['room_type'] ?? json['roomType'] ?? 'unknown',
      name: json['name'],
      floor: json['floor'] ?? json['floorNumber'] ?? 1,
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
      width: (json['width'] as num).toDouble(),
      length: (json['length'] as num).toDouble(),
      doors: (json['doors'] as List?)?.map((d) => Opening.fromJson(d)).toList() ?? [],
      windows: (json['windows'] as List?)?.map((w) => Opening.fromJson(w)).toList() ?? [],
    );
  }
}

/// Color palette for distinguishing rooms by type.
final Map<String, Color> _roomColors = {
  'living_room': const Color(0xFFE0F2FE),
  'dining_room': const Color(0xFFFCE7F3),
  'kitchen': const Color(0xFFFEF3C7),
  'bedroom_1': const Color(0xFFDBEAFE),
  'bedroom_2': const Color(0xFFE0E7FF),
  'bedroom_3': const Color(0xFFEDE9FE),
  'bedroom_4': const Color(0xFFF3E8FF),
  'bathroom_1': const Color(0xFFD1FAE5),
  'bathroom_2': const Color(0xFFD1FAE5),
  'bathroom_3': const Color(0xFFD1FAE5),
  'staircase': const Color(0xFFF1F5F9),
  'staircase_upper': const Color(0xFFF1F5F9),
};

const Color _defaultRoomColor = Color(0xFFF8FAFC);

/// Stateless widget that wraps the CustomPainter and handles layout calculations.
/// Supports filtering rooms by floor number.
class FloorPlanViewer extends StatelessWidget {
  final List<RoomLayout> rooms;
  final int? floorFilter;

  const FloorPlanViewer({Key? key, required this.rooms, this.floorFilter}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    // Filter rooms by floor if specified
    final displayRooms = floorFilter != null
        ? rooms.where((r) => r.floor == floorFilter).toList()
        : rooms;

    if (displayRooms.isEmpty) {
      return const Center(
        child: Text('No rooms to display for this floor.', style: TextStyle(color: Colors.grey)),
      );
    }

    double minX = displayRooms.map((r) => r.x).reduce(min);
    double minY = displayRooms.map((r) => r.y).reduce(min);
    double maxX = displayRooms.map((r) => r.x + r.width).reduce(max);
    double maxY = displayRooms.map((r) => r.y + r.length).reduce(max);

    double totalWidthFt = maxX - minX;
    double totalLengthFt = maxY - minY;

    return LayoutBuilder(
      builder: (context, constraints) {
        const padding = 40.0;
        final availableWidth = constraints.maxWidth - padding * 2;
        final availableHeight = constraints.maxHeight - padding * 2;

        // Scale to fit both width and height
        final scaleX = availableWidth / totalWidthFt;
        final scaleY = availableHeight / totalLengthFt;
        final scale = min(scaleX, scaleY);

        final canvasWidth = totalWidthFt * scale;
        final canvasHeight = totalLengthFt * scale;

        return Center(
          child: Container(
            padding: const EdgeInsets.all(padding),
            child: CustomPaint(
              size: Size(canvasWidth, canvasHeight),
              painter: FloorPlanPainter(
                rooms: displayRooms,
                scale: scale,
                minX: minX,
                maxY: maxY,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// CustomPainter that draws the floor plan.
class FloorPlanPainter extends CustomPainter {
  final List<RoomLayout> rooms;
  final double scale;
  final double minX;
  final double maxY;

  FloorPlanPainter({
    required this.rooms,
    required this.scale,
    required this.minX,
    required this.maxY,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Background Grid
    final gridPaint = Paint()
      ..color = const Color(0xFFF0F0F0)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    for (double i = 0; i <= size.width; i += scale) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), gridPaint);
    }
    for (double i = 0; i <= size.height; i += scale) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), gridPaint);
    }

    // Wall paint
    final wallPaint = Paint()
      ..color = const Color(0xFF334155)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;

    final doorPaint = Paint()
      ..color = const Color(0xFFFFFFFF)
      ..style = PaintingStyle.fill;

    final windowPaint = Paint()
      ..color = const Color(0xFFBAE6FD)
      ..style = PaintingStyle.fill;

    const labelStyle = TextStyle(
      color: Color(0xFF334155),
      fontSize: 13,
      fontWeight: FontWeight.w600,
      fontFamily: 'Roboto',
    );

    const dimStyle = TextStyle(
      color: Color(0xFF94A3B8),
      fontSize: 10,
      fontFamily: 'Roboto',
    );

    const areaStyle = TextStyle(
      color: Color(0xFFCBD5E1),
      fontSize: 9,
      fontFamily: 'Roboto',
    );

    for (var room in rooms) {
      // Invert Y axis for Flutter Canvas (0,0 is top-left)
      final drawX = (room.x - minX) * scale;
      final drawY = (maxY - (room.y + room.length)) * scale;
      final drawWidth = room.width * scale;
      final drawHeight = room.length * scale;

      final rect = Rect.fromLTWH(drawX, drawY, drawWidth, drawHeight);

      // 1. Draw floor fill with room-type color
      final fillColor = _roomColors[room.roomType] ?? _defaultRoomColor;
      final fillPaint = Paint()
        ..color = fillColor
        ..style = PaintingStyle.fill;
      canvas.drawRect(rect, fillPaint);

      // 2. Draw walls
      canvas.drawRect(rect, wallPaint);

      // 3. Draw openings
      for (var window in room.windows) {
        _drawOpening(canvas, window, drawX, drawY, drawWidth, drawHeight, windowPaint);
      }
      for (var door in room.doors) {
        _drawOpening(canvas, door, drawX, drawY, drawWidth, drawHeight, doorPaint);
      }

      // 4. Draw labels
      final cx = drawX + drawWidth / 2;
      final cy = drawY + drawHeight / 2;

      // Room name
      final roomName = room.name ?? _formatRoomName(room.roomType);
      _drawCenteredText(canvas, roomName, cx, cy - 12, labelStyle);

      // Dimensions
      _drawCenteredText(canvas, "${room.width}ft × ${room.length}ft", cx, cy + 6, dimStyle);

      // Area
      final area = (room.width * room.length).round();
      _drawCenteredText(canvas, "$area sqft", cx, cy + 20, areaStyle);
    }
  }

  void _drawCenteredText(Canvas canvas, String text, double cx, double cy, TextStyle style) {
    final textPainter = TextPainter(
      text: TextSpan(text: text, style: style),
      textDirection: TextDirection.ltr,
      textAlign: TextAlign.center,
    );
    textPainter.layout();
    textPainter.paint(canvas, Offset(cx - textPainter.width / 2, cy - textPainter.height / 2));
  }

  void _drawOpening(Canvas canvas, Opening opening, double drawX, double drawY, double drawWidth, double drawHeight, Paint paint) {
    const strokeOvercut = 5.0;

    final scaledOffset = opening.offset * scale;
    final scaledWidth = opening.width * scale;

    Rect openingRect;

    switch (opening.wall) {
      case 'north':
        openingRect = Rect.fromLTWH(drawX + scaledOffset, drawY - strokeOvercut / 2, scaledWidth, strokeOvercut);
        break;
      case 'south':
        openingRect = Rect.fromLTWH(drawX + scaledOffset, drawY + drawHeight - strokeOvercut / 2, scaledWidth, strokeOvercut);
        break;
      case 'east':
        openingRect = Rect.fromLTWH(drawX + drawWidth - strokeOvercut / 2, drawY + drawHeight - scaledOffset - scaledWidth, strokeOvercut, scaledWidth);
        break;
      case 'west':
        openingRect = Rect.fromLTWH(drawX - strokeOvercut / 2, drawY + drawHeight - scaledOffset - scaledWidth, strokeOvercut, scaledWidth);
        break;
      default:
        return;
    }

    canvas.drawRect(openingRect, paint);
  }

  String _formatRoomName(String type) {
    return type.split('_').map((word) {
      if (word.isEmpty) return '';
      return word[0].toUpperCase() + word.substring(1);
    }).join(' ');
  }

  @override
  bool shouldRepaint(covariant FloorPlanPainter oldDelegate) {
    return oldDelegate.rooms != rooms || oldDelegate.scale != scale;
  }
}
