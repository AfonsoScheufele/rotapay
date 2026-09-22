import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})
L.Marker.prototype.options.icon = DefaultIcon

interface Props {
  originLat: number
  originLng: number
  destLat: number
  destLng: number
  originLabel: string
  destLabel: string
}

export function FreightMap({
  originLat,
  originLng,
  destLat,
  destLng,
  originLabel,
  destLabel,
}: Props) {
  const centerLat = (originLat + destLat) / 2
  const centerLng = (originLng + destLng) / 2

  return (
    <div className="map-wrap">
      <MapContainer
        center={[centerLat, centerLng]}
        zoom={5}
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={[originLat, originLng]}>
          <Popup>
            <strong>Coleta</strong>
            <br />
            {originLabel}
          </Popup>
        </Marker>
        <Marker position={[destLat, destLng]}>
          <Popup>
            <strong>Entrega</strong>
            <br />
            {destLabel}
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  )
}
