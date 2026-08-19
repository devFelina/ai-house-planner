import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart'; 
import 'views/login_view.dart';
import 'views/register_view.dart';
import 'views/intake_view.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Make sure you have run `flutterfire configure` in your terminal
  // and import 'firebase_options.dart' to use the code below:
  // await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  runApp(
    const ProviderScope(child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override 
  Widget build(BuildContext context){
    //
    return MaterialApp(
      title: 'AI House Planner',
      debugShowCheckedModeBanner: false,
      theme:ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      //First screen is the login screen
      initialRoute:'/login',
      routes:{
        '/login': (context) => const LoginView(),
        '/register': (context) => const RegisterView(),
        '/land_submission': (context) => const IntakeView(),
      },

    );
  }
}