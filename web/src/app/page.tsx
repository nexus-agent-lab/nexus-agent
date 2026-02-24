import React from 'react';

/**
 * Interface representing a simple Plugin model.
 * Matches the expected response from the FastAPI /api/plugins/ endpoint.
 */
interface Plugin {
  id: string;
  name: string;
  description: string;
  version: string;
  author: string;
}

/**
 * Fetch plugins from the FastAPI backend.
 * Uses Next.js App Router server component data fetching.
 */
async function getPlugins(): Promise<Plugin[]> {
  // In a real scenario, the backend URL would be configurable via env vars.
  // We use the scaffolded endpoint. Note that we handle potential connection errors
  // since the backend might not be running.
  try {
    const res = await fetch('http://127.0.0.1:8000/api/plugins/', {
      // Revalidate frequently or set to no-store for real-time marketplace data
      cache: 'no-store',
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch plugins: ${res.statusText}`);
    }

    return await res.json();
  } catch (error) {
    console.error('Error fetching plugins:', error);
    return [];
  }
}

/**
 * Plugin Marketplace Page (Server Component)
 */
export default async function PluginMarketplace() {
  const plugins = await getPlugins();

  return (
    <main className="min-h-screen p-8 bg-gray-50 text-gray-900">
      <div className="max-w-5xl mx-auto">
        <header className="mb-10">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 mb-2">
            Plugin Marketplace
          </h1>
          <p className="text-lg text-gray-600">
            Discover and install plugins to extend your Nexus Agent.
          </p>
        </header>

        {plugins.length === 0 ? (
          <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100 text-center">
            <p className="text-gray-500">
              No plugins found or the backend API is currently unavailable.
            </p>
            <p className="text-sm text-gray-400 mt-2">
              Ensure the FastAPI server is running on http://127.0.0.1:8000.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {plugins.map((plugin) => (
              <div 
                key={plugin.id} 
                className="p-6 bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start mb-4">
                  <h2 className="text-xl font-bold text-gray-900">{plugin.name}</h2>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    v{plugin.version}
                  </span>
                </div>
                <p className="text-gray-600 mb-4 line-clamp-2">
                  {plugin.description}
                </p>
                <div className="text-sm text-gray-500 flex justify-between items-center">
                  <span>By {plugin.author}</span>
                  <button className="text-blue-600 hover:text-blue-800 font-medium">
                    Install
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
