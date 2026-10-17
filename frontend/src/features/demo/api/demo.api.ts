import { useQuery } from "@tanstack/react-query";

import { DEMO_QUERY_KEYS } from "@/features/demo/api/demo.keys";
import { DemoService } from "@/features/demo/api/demo.service";
import type { GetDemoParams } from "@/features/demo/types";

export const useGetAllDemo = (params: GetDemoParams) => {
  return useQuery({
    queryKey: DEMO_QUERY_KEYS.list(params),
    queryFn: () => DemoService.getAll(params),
  });
};
