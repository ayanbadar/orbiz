import type {
  Paginated,
  Store,
  StoreCreateRequest,
} from "@/features/stores/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/stores";

export class StoreService {
  static async list(): Promise<Store[]> {
    const response = await api.get<Paginated<Store> | Store[]>(`${ROOT}/`);
    const data = response.data;
    return Array.isArray(data) ? data : data.results;
  }

  static async me(): Promise<Store> {
    const response = await api.get<Store>(`${ROOT}/me/`);
    return response.data;
  }

  static async create(body: StoreCreateRequest): Promise<Store> {
    const response = await api.post<Store>(`${ROOT}/`, body);
    return response.data;
  }

  static async setDefault(storeId: number): Promise<Store> {
    const response = await api.post<Store>(`${ROOT}/set-default/`, {
      store_id: storeId,
    });
    return response.data;
  }
}
