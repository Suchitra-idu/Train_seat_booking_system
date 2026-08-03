<script>
  // The one place lucide is imported (D27): a name -> component lookup so callers write
  // <Icon name="train" /> instead of importing a different lucide component per file.
  import {
    TrainFront,
    Search,
    Check,
    CircleCheck,
    Lock,
    TriangleAlert,
    Clock,
    Ticket,
    Armchair,
    QrCode,
    Printer,
    ArrowRight,
    Banknote,
    ShieldCheck,
    X,
  } from "lucide-svelte";

  const ICONS = {
    train: TrainFront,
    search: Search,
    check: Check,
    "circle-check": CircleCheck,
    lock: Lock,
    alert: TriangleAlert,
    clock: Clock,
    ticket: Ticket,
    seat: Armchair,
    qr: QrCode,
    printer: Printer,
    "arrow-right": ArrowRight,
    banknote: Banknote,
    "shield-check": ShieldCheck,
    close: X,
  };

  let { name, class: cls = "size-4" } = $props();
  const Cmp = $derived(ICONS[name] ?? TrainFront);
</script>

<Cmp class={cls} />
