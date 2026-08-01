// L0 view-core: shape a TrainOptionOut for the train-list card. Pure.

import { classLabel } from "./seatmap.js";
import { formatDuration } from "./time.js";

/** @param {object} option TrainOptionOut */
export function trainRow(option) {
  return {
    tripId: option.trip_id,
    trainNo: option.train_no,
    trainName: option.train_name,
    depart: option.depart,
    arrive: option.arrive,
    duration: formatDuration(option.duration_min),
    freeSeats: option.free_seats,
    soldOut: option.free_seats === 0,
    fromFare: option.from_fare,
    classes: option.classes.map((c) => ({
      travelClass: c.travel_class,
      label: classLabel(c.travel_class),
      freeSeats: c.free_seats,
      fare: c.fare,
    })),
  };
}

export function trainRows(options) {
  return (options || []).map(trainRow);
}
