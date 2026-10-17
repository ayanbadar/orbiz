export type DemoItem = {
  id: string;
  name: string;
  category: string;
};

export type GetDemoParams = {
  search?: string;
  category?: string;
};
