using FirebaseAdmin;
using Google.Apis.Auth.OAuth2;
using HousePlanner.API.Middleware;
using HousePlanner.API.Services;
using Microsoft.OpenApi.Models;
using Microsoft.EntityFrameworkCore;
using HousePlanner.API.Data;

var builder = WebApplication.CreateBuilder(args);

// Add PostgreSQL DbContext
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));

// 1. Add CORS services allowing our React frontend client
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowReactApp", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

// 2. Add controllers and endpoints API exploration
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();

// 3. Configure Swagger/OpenAPI
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "HousePlanner API",
        Version = "v1",
        Description = "Core backend Web API for AI home design and cost planning."
    });
    
    // Add Bearer token authorize options to Swagger UI for verification testing
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Description = "Firebase JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\"",
        Name = "Authorization",
        In = ParameterLocation.Header,
        Type = SecuritySchemeType.ApiKey,
        Scheme = "Bearer"
    });

    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            Array.Empty<string>()
        }
    });
});

// 4. Register application services
builder.Services.AddScoped<IFirebaseAuthService, FirebaseAuthService>();
builder.Services.AddScoped<IPricingService, PricingService>();

// 5. Initialize Firebase Admin SDK
var serviceAccountPath = builder.Configuration["Firebase:ServiceAccountPath"];
var fullPath = Path.Combine(builder.Environment.ContentRootPath, serviceAccountPath ?? "firebase-service-account.json");

if (!string.IsNullOrEmpty(serviceAccountPath) && File.Exists(fullPath))
{
    try
    {
        FirebaseApp.Create(new AppOptions
        {
            Credential = GoogleCredential.FromFile(fullPath)
        });
        Console.WriteLine($"[Firebase SDK] Successfully initialized FirebaseApp using service account credentials from: {fullPath}");
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[Firebase SDK Error] Failed to initialize FirebaseApp from file: {ex.Message}");
    }
}
else
{
    var envCreds = Environment.GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS");
    if (!string.IsNullOrEmpty(envCreds) && File.Exists(envCreds))
    {
        try
        {
            FirebaseApp.Create();
            Console.WriteLine("[Firebase SDK] Successfully initialized FirebaseApp using GOOGLE_APPLICATION_CREDENTIALS environment variable.");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[Firebase SDK Error] Failed to initialize FirebaseApp from env variable: {ex.Message}");
        }
    }
    else
    {
        Console.WriteLine("[Firebase SDK Warning] No Firebase service account file or environment variable found.");
        Console.WriteLine("ID Token verification will fail. Place your credentials in 'firebase-service-account.json' to test real validation.");
        
        // Attempt fallback default initialization to prevent crash if running dry or mock
        try
        {
            FirebaseApp.Create(new AppOptions
            {
                Credential = GoogleCredential.GetApplicationDefault()
            });
        }
        catch
        {
            // Suppress fallback error in console as we have already warned the developer
        }
    }
}

var app = builder.Build();

// Auto-create database tables and seed data
using (var scope = app.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
    context.Database.EnsureCreated();

    // Seed PricingData
    if (!context.PricingItems.Any())
    {
        var seedData = new List<HousePlanner.API.Entities.PricingData>
        {
            new HousePlanner.API.Entities.PricingData 
            { 
                ItemName = "Cement", 
                Category = "material", 
                UnitCostLkr = 2500m, 
                Unit = "bag", 
                TerrainMultiplier = new HousePlanner.API.Entities.TerrainMultiplierData { Flat = 1.0m, Hillside = 1.25m, Coastal = 1.35m }, 
                UpdatedAt = DateTimeOffset.UtcNow 
            },
            new HousePlanner.API.Entities.PricingData 
            { 
                ItemName = "Steel", 
                Category = "material", 
                UnitCostLkr = 350000m, 
                Unit = "ton", 
                TerrainMultiplier = new HousePlanner.API.Entities.TerrainMultiplierData { Flat = 1.0m, Hillside = 1.2m, Coastal = 1.5m }, 
                UpdatedAt = DateTimeOffset.UtcNow 
            },
            new HousePlanner.API.Entities.PricingData 
            { 
                ItemName = "Flooring", 
                Category = "material", 
                UnitCostLkr = 8000m, 
                Unit = "sqm", 
                TerrainMultiplier = new HousePlanner.API.Entities.TerrainMultiplierData { Flat = 1.0m, Hillside = 1.1m, Coastal = 1.1m }, 
                UpdatedAt = DateTimeOffset.UtcNow 
            },
            new HousePlanner.API.Entities.PricingData 
            { 
                ItemName = "Construction Labour", 
                Category = "labour", 
                UnitCostLkr = 4500m, 
                Unit = "day", 
                TerrainMultiplier = new HousePlanner.API.Entities.TerrainMultiplierData { Flat = 1.0m, Hillside = 1.3m, Coastal = 1.2m }, 
                UpdatedAt = DateTimeOffset.UtcNow 
            }
        };

        context.PricingItems.AddRange(seedData);
        context.SaveChanges();
    }
}

// 6. Register exception-handling middleware early in request pipeline
app.UseMiddleware<ExceptionHandlingMiddleware>();

// Enable Swagger in Development environment
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "HousePlanner API v1");
        c.RoutePrefix = "swagger"; // Exposes Swagger at http://localhost:<port>/swagger
    });
}

// Disable default HTTPS redirect for ease of local testing in CORS environments if desired,
// but keep it active and ensure client URLs match.
app.UseHttpsRedirection();

// Apply CORS Policy
app.UseCors("AllowReactApp");

app.UseAuthorization();

// Map controllers
app.MapControllers();

app.Run();
