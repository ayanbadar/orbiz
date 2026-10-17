import type { DemoItem, GetDemoParams } from "@/features/demo/types";

const MOCK_ITEMS: DemoItem[] = [
  { id: "1", name: "Oak Dining Table", category: "furniture" },
  { id: "2", name: "Linen Sofa", category: "furniture" },
  { id: "3", name: "Ceramic Vase", category: "decor" },
  { id: "4", name: "Brass Lamp", category: "lighting" },
  { id: "5", name: "Wool Rug", category: "decor" },
];

/**
 * Demo service — uses local mock data so the foundation works without a backend.
 * Replace the body of these methods with `api.get/post/...` when the API is ready.
 */
export class DemoService {
  static path = "/demo";

  static async getAll(params: GetDemoParams = {}): Promise<DemoItem[]> {
    await delay(300);

    const search = params.search?.trim().toLowerCase();
    const category = params.category?.trim().toLowerCase();

    return MOCK_ITEMS.filter((item) => {
      const matchesSearch = !search || item.name.toLowerCase().includes(search);
      const matchesCategory =
        !category || category === "all" || item.category === category;

      return matchesSearch && matchesCategory;
    });
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
