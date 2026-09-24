import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { NoData, PageHeader, Skeleton } from "../components/ui";
import { CategoryRanking } from "../components/CategoryRanking";

export default function Categories() {
  const { data, isLoading } = useQuery({ queryKey: ["byCategory"], queryFn: api.byCategory });

  if (isLoading) {
    return (
      <div aria-busy="true">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="mt-6 h-96" />
      </div>
    );
  }
  const byCategory = data?.by_category ?? {};
  if (Object.keys(byCategory).length === 0) return <NoData />;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Categories" subtitle="Everything you spent, largest first." />
      <CategoryRanking data={byCategory} title="Spending by category" />
    </div>
  );
}
