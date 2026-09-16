import "dotenv/config";
import { genkit, z } from "genkit";
import { googleAI } from "@genkit-ai/googleai";
import express from "express";
import cors from "cors";

// Initialize Genkit
const ai = genkit({
  plugins: [googleAI()],
  model: "googleai/gemini-2.5-flash", 
});

// Define the Action Glass SEO Flow
export const actionGlassSeoFlow = ai.defineFlow(
  {
    name: "actionGlassSeoFlow",
    inputSchema: z.object({
      service: z.string(),
      location: z.string().default("Jenison, MI"),
    }),
    outputSchema: z.object({
      adHeadline: z.string(),
      adBody: z.string(),
      keywords: z.array(z.string()),
      seoTitle: z.string(),
      metaDescription: z.string(),
    }),
  },
  async ({ service, location }) => {
    const prompt = `You are an expert marketer for 'Action Glass', a premier Auto Glass and Residential Glass specialist based in ${location}. 
    The user wants to run a campaign for the following service: ${service}.
    Generate a high-converting Google Ad (headline and body), a list of 5 SEO keywords, an SEO page title, and a meta description.
    Make it highly persuasive and emphasize local trust and speed.`;

    const response = await ai.generate({
      prompt,
      output: {
        schema: z.object({
          adHeadline: z.string(),
          adBody: z.string(),
          keywords: z.array(z.string()),
          seoTitle: z.string(),
          metaDescription: z.string(),
        })
      }
    });

    return response.output;
  }
);

// Set up an Express server to expose the Genkit flows to the Python backend
const app = express();
app.use(cors());
app.use(express.json());

app.post("/api/actionGlassSeoFlow", async (req, res) => {
  try {
    const { service, location } = req.body;
    const result = await actionGlassSeoFlow({ service: service || "Windshield Replacement", location: location || "Jenison, MI" });
    res.json({ result });
  } catch (error: any) {
    console.error("Genkit Error:", error);
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Genkit microservice is running on http://localhost:${PORT}`);
});
